"""arq pipeline tasks: download -> transcribe -> segment -> render.

Each task:
- owns one :class:`ProcessingJob` row (created if absent, reset on retry),
- updates ``Project.status`` and job ``progress_pct``,
- is idempotent (safe to re-run) and retryable (raises on failure so arq
  retries up to ``max_tries``),
- chains to the next stage via ``ctx['redis'].enqueue_job`` on success.

DB access is synchronous (SQLAlchemy ``Session``); acceptable for the MVP
worker. Heavy CPU/IO (whisper, ffmpeg) also runs inline in the task.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.database import SessionLocal
from app.models.clip import Clip, ClipStatus
from app.models.clip_caption import ClipCaption
from app.models.processing_job import JobStatus, JobType, ProcessingJob
from app.models.project import Project, ProjectStatus, SourceType
from app.models.transcript import Transcript
from app.services import rendering, segmentation, storage, transcription
from app.services.media_url import source_key
from app.services.ssrf import validate_public_url

logger = logging.getLogger("segmently.workers.pipeline")

_STATUS_FOR_JOB = {
    JobType.download: ProjectStatus.downloading,
    JobType.transcribe: ProjectStatus.transcribing,
    JobType.segment: ProjectStatus.segmenting,
    JobType.render: ProjectStatus.rendering,
}


@contextmanager
def _session() -> Iterator[Any]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_or_create_job(db: Any, project_id: int, job_type: JobType) -> ProcessingJob:
    job = (
        db.query(ProcessingJob)
        .filter(
            ProcessingJob.project_id == project_id,
            ProcessingJob.job_type == job_type,
        )
        .order_by(ProcessingJob.id.desc())
        .first()
    )
    if job is None:
        job = ProcessingJob(project_id=project_id, job_type=job_type)
        db.add(job)
        db.flush()
    return job


def _start_job(db: Any, project: Project, job_type: JobType) -> ProcessingJob:
    job = _get_or_create_job(db, project.id, job_type)
    job.status = JobStatus.running
    job.progress_pct = 0
    job.started_at = _now()
    job.finished_at = None
    job.error_message = None
    project.status = _STATUS_FOR_JOB[job_type]
    project.error_message = None
    db.flush()
    return job


def _finish_job(db: Any, job: ProcessingJob) -> None:
    job.status = JobStatus.completed
    job.progress_pct = 100
    job.finished_at = _now()


def _fail(db: Any, project: Project, job: ProcessingJob, exc: Exception) -> None:
    job.status = JobStatus.failed
    job.finished_at = _now()
    job.error_message = str(exc)[:2000]
    project.status = ProjectStatus.failed
    project.error_message = f"{job.job_type.value}: {exc}"[:2000]


def _load_project(db: Any, project_id: int) -> Project | None:
    return db.get(Project, project_id)


def _ffprobe_duration(path: str) -> float | None:
    binary = shutil.which(settings.FFPROBE_BINARY)
    if not binary:
        return None
    try:
        out = subprocess.run(  # noqa: S603
            [
                binary,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        return float(out.stdout.strip())
    except (subprocess.SubprocessError, ValueError, OSError):
        return None


def _work_root() -> str:
    try:
        os.makedirs(settings.MEDIA_WORK_DIR, exist_ok=True)
        return settings.MEDIA_WORK_DIR
    except OSError:
        return tempfile.gettempdir()


# --------------------------------------------------------------------------- #
# Stage 1: download                                                            #
# --------------------------------------------------------------------------- #
async def run_download(ctx: dict[str, Any], project_id: int) -> str:
    """Fetch the source URL into object storage, then chain transcription."""
    with _session() as db:
        project = _load_project(db, project_id)
        if project is None:
            logger.warning("run_download: project %s gone", project_id)
            return "missing"
        if project.source_type != SourceType.url or not project.source_url:
            logger.info("run_download: project %s is not a URL import - skipping", project_id)
            await ctx["redis"].enqueue_job("run_transcribe", project_id)
            return "skipped"
        _start_job(db, project, JobType.download)
        url = project.source_url

    workdir = tempfile.mkdtemp(prefix="segmently-dl-", dir=_work_root())
    local = os.path.join(workdir, "source")
    try:
        # These block (network, subprocess, boto3) - run off the event loop so
        # the arq heartbeat keeps ticking and other jobs aren't starved. A hard
        # wall-clock cap stops a stalled server holding the job forever.
        remote_title = await asyncio.wait_for(
            asyncio.to_thread(_fetch_source, url, local, workdir),
            timeout=settings.DOWNLOAD_TIMEOUT_SECONDS,
        )
        if not os.path.exists(local) or os.path.getsize(local) < 1024:
            raise RuntimeError("The URL did not return a downloadable video file.")
        duration = await asyncio.to_thread(_ffprobe_duration, local)
        if duration is None:
            raise RuntimeError(
                "That link isn't a video file (FFmpeg couldn't read it). Use a "
                "direct video URL or upload the file."
            )
        key = source_key(project_id, "mp4")
        await asyncio.to_thread(
            storage.upload_file, local, key, content_type="video/mp4"
        )
        size = os.path.getsize(local)
        with _session() as db:
            project = _load_project(db, project_id)
            job = _get_or_create_job(db, project_id, JobType.download)
            project.storage_key = key
            project.duration_seconds = duration
            project.file_size_bytes = size
            if remote_title and _is_placeholder_title(project.title, url):
                project.title = remote_title[:255]
            _finish_job(db, job)
        await ctx["redis"].enqueue_job("run_transcribe", project_id)
        return key
    except Exception as exc:  # noqa: BLE001 - record + re-raise for retry
        logger.exception("run_download failed for %s", project_id)
        with _session() as db:
            project = _load_project(db, project_id)
            job = _get_or_create_job(db, project_id, JobType.download)
            if project is not None:
                _fail(db, project, job, exc)
        raise
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


_MAX_REDIRECTS = 5

# Direct-download file extensions - anything else is treated as a page URL and
# handed to yt-dlp (which only runs for the allow-listed hosts below).
_DIRECT_MEDIA_EXTS = (".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi", ".mpeg", ".mpg")

# Hosts yt-dlp is permitted to fetch from. Keeps the SSRF surface small: an
# arbitrary URL cannot be turned into a yt-dlp fetch of an internal service.
_YTDLP_ALLOWED_HOSTS = (
    "youtube.com",
    "youtu.be",
    "vimeo.com",
    "twitch.tv",
    "tiktok.com",
    "dailymotion.com",
    "streamable.com",
    "facebook.com",
    "fb.watch",
    "instagram.com",
)


def _host_allows_ytdlp(url: str) -> bool:
    from urllib.parse import urlparse

    host = (urlparse(url).hostname or "").lower().lstrip("www.")
    return any(host == h or host.endswith("." + h) for h in _YTDLP_ALLOWED_HOSTS)


def _is_placeholder_title(title: str | None, url: str) -> bool:
    """True if *title* is the weak URL-derived default (e.g. "watch" for YouTube)."""
    if not title:
        return True
    weak = {"watch", "video", "index", "embed", "v", url}
    return title.strip().lower() in weak or len(title.strip()) <= 2


def _fetch_source(url: str, dest: str, workdir: str) -> str | None:
    """Fetch *url* into *dest* (a plain file path, no extension).

    Direct media links are streamed over HTTP with the SSRF-safe fetcher.
    Platform page URLs (YouTube, Vimeo, Twitch, ...) go through yt-dlp.

    Returns the remote media title when one is available (yt-dlp path), else None.
    """
    from urllib.parse import urlparse

    path = (urlparse(url).path or "").lower()
    if path.endswith(_DIRECT_MEDIA_EXTS):
        validate_public_url(url)
        _download_url(url, dest)
        return None

    if _host_allows_ytdlp(url):
        return _download_with_ytdlp(url, dest, workdir)

    raise ValueError(
        "Unsupported URL. Provide a direct video file link, or a page URL from "
        "YouTube, Vimeo, Twitch, TikTok, Dailymotion, Streamable, Facebook or "
        "Instagram."
    )


def _download_with_ytdlp(url: str, dest: str, workdir: str) -> str | None:
    """Download the best <= size-cap MP4 for *url* using yt-dlp, into *dest*.

    Returns the video title reported by yt-dlp, if any.
    """
    try:
        import yt_dlp
    except ImportError as exc:  # pragma: no cover - dependency missing
        raise RuntimeError("yt-dlp is not installed in the worker image") from exc

    out_template = os.path.join(workdir, "ytdl.%(ext)s")
    max_height = settings.YTDLP_MAX_HEIGHT
    ydl_opts = {
        "outtmpl": {"default": out_template},
        # Cap the resolution - clips are 1080x1920 and cropped from the centre,
        # so a >720p source is wasted bandwidth. Prefer a single progressive
        # file, then muxed video+audio, with progressively looser fallbacks.
        "format": (
            f"b[height<={max_height}][ext=mp4]/"
            f"bv*[height<={max_height}][ext=mp4]+ba[ext=m4a]/"
            f"b[height<={max_height}]/"
            "b[ext=mp4]/b"
        ),
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "retries": 3,
        "socket_timeout": 60,
        "max_filesize": settings.MAX_UPLOAD_BYTES,
        # YouTube blocks bare requests from datacenter IPs ("Sign in to confirm
        # you're not a bot"). Trying several player clients dodges it for many
        # videos; a cookies file (YTDLP_COOKIES_FILE) is the reliable fallback.
        "extractor_args": {
            "youtube": {"player_client": ["web_safari", "mweb", "tv", "android", "default"]}
        },
    }
    cookies = settings.YTDLP_COOKIES_FILE
    if cookies and os.path.exists(cookies):
        ydl_opts["cookiefile"] = cookies
        logger.info("yt-dlp: using cookies file %s", cookies)
    if settings.YTDLP_PROXY:
        ydl_opts["proxy"] = settings.YTDLP_PROXY
        logger.info("yt-dlp: routing through configured proxy")
    # Only pin ffmpeg's location when an absolute path is configured; otherwise
    # let yt-dlp find it on PATH (a bare "ffmpeg" here breaks yt-dlp's lookup).
    if os.path.isabs(settings.FFMPEG_BINARY):
        ydl_opts["ffmpeg_location"] = settings.FFMPEG_BINARY
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except Exception as exc:  # noqa: BLE001 - yt-dlp errors carry unpicklable tracebacks
        msg = str(exc).replace("\n", " ")[:400]
        if "confirm you" in msg or "bot" in msg or "cookies" in msg.lower():
            raise RuntimeError(
                "YouTube is blocking downloads from this server's IP. Set a "
                "residential proxy (YTDLP_PROXY), add a cookies.txt "
                "(YTDLP_COOKIES_FILE), or upload the file directly."
            ) from None
        raise RuntimeError(f"yt-dlp could not fetch this URL: {msg}") from None

    produced = [
        os.path.join(workdir, f)
        for f in os.listdir(workdir)
        if f.startswith("ytdl.") and not f.endswith(".part")
    ]
    if not produced:
        raise RuntimeError("yt-dlp produced no output file")
    src = max(produced, key=os.path.getsize)
    if os.path.getsize(src) > settings.MAX_UPLOAD_BYTES:
        raise ValueError("Downloaded media exceeds the maximum allowed size")
    shutil.move(src, dest)

    title = (info or {}).get("title") if isinstance(info, dict) else None
    return title.strip() if isinstance(title, str) and title.strip() else None


def _download_url(url: str, dest: str) -> None:
    """Stream a remote file to *dest* with a size cap.

    SSRF-safe: redirects are **not** followed automatically. Every hop
    (including the original URL) is re-validated with ``validate_public_url``
    before a request is made, closing the "public URL 302s to 169.254.169.254"
    bypass.
    """
    import httpx

    max_bytes = settings.MAX_UPLOAD_BYTES
    written = 0
    current = url
    # A browser-like UA - many hosts 403 the default httpx agent.
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
        "Accept": "*/*",
    }
    with httpx.Client(
        follow_redirects=False,
        timeout=60.0,
        headers=headers,
        proxy=settings.YTDLP_PROXY or None,
    ) as client:
        for _hop in range(_MAX_REDIRECTS + 1):
            validate_public_url(current)
            with client.stream("GET", current) as resp:
                if resp.is_redirect:
                    location = resp.headers.get("location")
                    if not location:
                        raise ValueError("Redirect response without a Location header")
                    current = str(httpx.URL(current).join(location))
                    continue
                resp.raise_for_status()
                with open(dest, "wb") as fh:
                    for chunk in resp.iter_bytes(chunk_size=1 << 20):
                        written += len(chunk)
                        if written > max_bytes:
                            raise ValueError(
                                "Remote file exceeds the maximum allowed size"
                            )
                        fh.write(chunk)
                return
    raise ValueError("Too many redirects while fetching the source URL")


# --------------------------------------------------------------------------- #
# Stage 2: transcribe                                                          #
# --------------------------------------------------------------------------- #
async def run_transcribe(ctx: dict[str, Any], project_id: int) -> str:
    """Transcribe the stored source, persist the transcript, chain segmentation."""
    with _session() as db:
        project = _load_project(db, project_id)
        if project is None:
            return "missing"
        if not project.storage_key:
            raise RuntimeError("run_transcribe: project has no storage_key")
        _start_job(db, project, JobType.transcribe)
        key = project.storage_key
        existing = (
            db.query(Transcript).filter(Transcript.project_id == project_id).first()
        )
        already_done = existing is not None

    if already_done:
        logger.info("Transcript already present for %s - skipping to segment", project_id)
    else:
        workdir = tempfile.mkdtemp(prefix="segmently-tr-", dir=_work_root())
        local = os.path.join(workdir, "source")
        try:
            await asyncio.to_thread(storage.download_file, key, local)
            result = await asyncio.to_thread(transcription.transcribe, local)
            with _session() as db:
                project = _load_project(db, project_id)
                job = _get_or_create_job(db, project_id, JobType.transcribe)
                db.query(Transcript).filter(
                    Transcript.project_id == project_id
                ).delete()
                db.add(
                    Transcript(
                        project_id=project_id,
                        language=result.get("language"),
                        full_text=result.get("full_text", ""),
                        segments=result.get("segments", []),
                    )
                )
                _finish_job(db, job)
        except Exception as exc:  # noqa: BLE001
            logger.exception("run_transcribe failed for %s", project_id)
            with _session() as db:
                project = _load_project(db, project_id)
                job = _get_or_create_job(db, project_id, JobType.transcribe)
                if project is not None:
                    _fail(db, project, job, exc)
            raise
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    await ctx["redis"].enqueue_job("run_segment", project_id)
    return "ok"


# --------------------------------------------------------------------------- #
# Stage 3: segment                                                             #
# --------------------------------------------------------------------------- #
async def run_segment(ctx: dict[str, Any], project_id: int) -> str:
    """Run LLM segment detection, create Clip rows, enqueue a render per clip."""
    with _session() as db:
        project = _load_project(db, project_id)
        if project is None:
            return "missing"
        _start_job(db, project, JobType.segment)
        transcript = (
            db.query(Transcript).filter(Transcript.project_id == project_id).first()
        )
        if transcript is None:
            raise RuntimeError("run_segment: no transcript for project")
        transcript_payload = {
            "language": transcript.language,
            "full_text": transcript.full_text,
            "segments": transcript.segments or [],
        }
        user_id = project.user_id

    try:
        detected = await asyncio.to_thread(
            segmentation.detect_segments, transcript_payload
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("run_segment failed for %s", project_id)
        with _session() as db:
            project = _load_project(db, project_id)
            job = _get_or_create_job(db, project_id, JobType.segment)
            if project is not None:
                _fail(db, project, job, exc)
        raise

    caption_index = transcript_payload["segments"]
    clip_ids: list[int] = []
    with _session() as db:
        project = _load_project(db, project_id)
        job = _get_or_create_job(db, project_id, JobType.segment)
        # Idempotent: drop any clips from a previous run.
        db.query(Clip).filter(Clip.project_id == project_id).delete()
        db.flush()
        for seg in detected:
            clip = Clip(
                project_id=project_id,
                user_id=user_id,
                title=seg["title"],
                start_seconds=seg["start"],
                end_seconds=seg["end"],
                duration_seconds=round(seg["end"] - seg["start"], 2),
                aspect_ratio="9:16",
                status=ClipStatus.queued,
                score=seg["score"],
                score_reason=seg["score_reason"],
            )
            db.add(clip)
            db.flush()
            db.add(
                ClipCaption(
                    clip_id=clip.id,
                    segments=_captions_within(caption_index, seg["start"], seg["end"]),
                    edited=False,
                )
            )
            clip_ids.append(clip.id)
        _finish_job(db, job)
        if not clip_ids:
            project.status = ProjectStatus.completed

    for clip_id in clip_ids:
        await ctx["redis"].enqueue_job("run_render", clip_id)
    return f"{len(clip_ids)} clips"


def _captions_within(
    segments: list[dict[str, Any]], start: float, end: float
) -> list[dict[str, Any]]:
    return [
        {
            "start": float(s.get("start", 0.0)),
            "end": float(s.get("end", 0.0)),
            "text": str(s.get("text", "")).strip(),
        }
        for s in segments
        if float(s.get("end", 0.0)) > start and float(s.get("start", 0.0)) < end
    ]


# --------------------------------------------------------------------------- #
# Stage 4: render                                                              #
# --------------------------------------------------------------------------- #
async def run_render(ctx: dict[str, Any], clip_id: int) -> str:
    """Render one clip with FFmpeg; mark the project completed when all are done."""
    with _session() as db:
        clip = db.get(Clip, clip_id)
        if clip is None:
            return "missing"
        project = _load_project(db, clip.project_id)
        if project is None:
            return "missing"
        _start_job(db, project, JobType.render)
        clip.status = ClipStatus.rendering
        caption = (
            db.query(ClipCaption).filter(ClipCaption.clip_id == clip_id).first()
        )
        ctx_data = {
            "project_id": project.id,
            "source_key": project.storage_key,
            "start": clip.start_seconds,
            "end": clip.end_seconds,
            "style": clip.caption_style,
            "captions": (caption.segments if caption else []) or [],
        }

    if not ctx_data["source_key"]:
        raise RuntimeError("run_render: project has no source storage_key")

    try:
        out_key = await asyncio.to_thread(
            rendering.render_clip,
            ctx_data["source_key"],
            ctx_data["start"],
            ctx_data["end"],
            ctx_data["captions"],
            ctx_data["style"],
            project_id=ctx_data["project_id"],
            clip_id=clip_id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("run_render failed for clip %s", clip_id)
        with _session() as db:
            clip = db.get(Clip, clip_id)
            if clip is not None:
                clip.status = ClipStatus.failed
            project = _load_project(db, ctx_data["project_id"])
            job = _get_or_create_job(db, ctx_data["project_id"], JobType.render)
            if project is not None:
                _fail(db, project, job, exc)
        raise

    with _session() as db:
        clip = db.get(Clip, clip_id)
        clip.storage_key = out_key
        clip.status = ClipStatus.ready
        project = _load_project(db, clip.project_id)
        job = _get_or_create_job(db, clip.project_id, JobType.render)
        # Flush so this clip's new status is visible to the aggregate query
        # below (the session runs with autoflush=False).
        db.flush()
        remaining = (
            db.query(Clip)
            .filter(
                Clip.project_id == clip.project_id,
                Clip.status.notin_([ClipStatus.ready, ClipStatus.failed]),
            )
            .count()
        )
        if remaining == 0:
            _finish_job(db, job)
            project.status = ProjectStatus.completed
    return out_key
