"""FFmpeg-based clip rendering: 9:16 vertical crop + burned-in captions.

``render_clip`` downloads the source segment, builds an FFmpeg command that
scales/crops to 1080x1920, burns captions, and encodes h264/aac, then
uploads the result and returns its storage key.

Requires the ``ffmpeg`` binary on PATH (worker image only - never the API
image). No Python FFmpeg wrapper dependency is used; we shell out via
``subprocess``.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from typing import Any, Sequence

from app.config import settings
from app.services import storage
from app.services.media_url import clip_key

logger = logging.getLogger("segmently.services.rendering")

TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920

# Caption layout (in the 1080x1920 target space).
_CAPTION_SIDE_MARGIN = 120          # keeps text off the rounded phone edges
_CAPTION_BOTTOM_MARGIN = 340        # lift captions above the platform UI strip
_CAPTION_MAX_CHARS = 30             # wrap long transcript lines into short cues
_CAPTION_MIN_CUE_SECONDS = 0.7


class RenderingError(RuntimeError):
    """Raised when FFmpeg is missing or a render command fails."""


def _broll_enabled(style: dict[str, Any] | None) -> bool:
    """B-roll runs when the clip opts in, or globally via ``BROLL_ENABLED``."""
    choice = (style or {}).get("broll")
    if isinstance(choice, bool):
        return choice
    return bool(settings.BROLL_ENABLED)


def _plan_broll(
    caption_segments: Sequence[dict[str, Any]] | None,
    start: float,
    end: float,
    style: dict[str, Any] | None,
    workdir: str,
) -> list[dict[str, Any]]:
    """Return ``[{"start","end","path","query"}]`` cutaways, or [] if disabled/none."""
    if not caption_segments or not _broll_enabled(style) or not settings.PEXELS_API_KEY:
        return []
    try:
        from app.services import broll as broll_service

        overlays = broll_service.build_broll_overlays(
            list(caption_segments), start, end, workdir
        )
        logger.info("B-roll: %d cutaway(s) prepared", len(overlays))
        return overlays
    except Exception:  # noqa: BLE001 - b-roll must never break a render
        logger.exception("B-roll planning failed - rendering without it")
        return []


def _ensure_ffmpeg() -> str:
    binary = settings.FFMPEG_BINARY
    resolved = shutil.which(binary)
    if not resolved:
        # TODO: install ffmpeg in the worker Docker image (DEVOPS-AGENT owns it).
        raise RenderingError(
            f"'{binary}' not found on PATH - the worker image must bundle FFmpeg."
        )
    return resolved


def _seconds_to_ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours}:{minutes:02d}:{secs:05.2f}"


def _escape_ass(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")").replace("\n", " ")


def _chunk_caption(text: str, start: float, end: float) -> list[tuple[float, float, str]]:
    """Split a transcript line into short, phone-friendly caption cues.

    Long sentences from the transcript overflow a vertical frame, so each is
    broken into <= ``_CAPTION_MAX_CHARS`` pieces on word boundaries, with the
    cue's duration shared out in proportion to each piece's length.
    """
    words = text.split()
    if not words:
        return []

    pieces: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > _CAPTION_MAX_CHARS and current:
            pieces.append(current)
            current = word
        else:
            current = candidate
    if current:
        pieces.append(current)

    total_chars = sum(len(p) for p in pieces) or 1
    span = max(end - start, _CAPTION_MIN_CUE_SECONDS * len(pieces))
    cues: list[tuple[float, float, str]] = []
    cursor = start
    for piece in pieces:
        share = span * (len(piece) / total_chars)
        cues.append((cursor, cursor + share, piece))
        cursor += share
    return cues


def _build_ass_subtitles(
    caption_segments: Sequence[dict[str, Any]],
    clip_start: float,
    style: dict[str, Any] | None,
) -> str:
    """Return an ASS subtitle document for the clip, times rebased to 0."""
    style = style or {}
    # "Noto Sans" ships with the worker image and covers Latin + Indic + CJK etc.
    # libass falls back through fontconfig for any glyphs it still lacks.
    font = str(style.get("font", "Noto Sans"))
    font_size = int(style.get("font_size", 52))
    primary = str(style.get("primary_colour", "&H00FFFFFF"))
    outline = str(style.get("outline_colour", "&H00000000"))
    side = int(style.get("side_margin", _CAPTION_SIDE_MARGIN))
    bottom = int(style.get("bottom_margin", _CAPTION_BOTTOM_MARGIN))
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {TARGET_WIDTH}\n"
        f"PlayResY: {TARGET_HEIGHT}\n"
        "WrapStyle: 0\n"
        "ScaledBorderAndShadow: yes\n"
        "YCbCr Matrix: TV.709\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, "
        "BackColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{font},{font_size},{primary},{outline},&H66000000,"
        f"-1,0,1,5,2,2,{side},{side},{bottom},1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
        "Effect, Text\n"
    )
    lines: list[str] = []
    for seg in caption_segments:
        seg_start = float(seg.get("start", 0.0)) - clip_start
        seg_end = float(seg.get("end", 0.0)) - clip_start
        if seg_end <= 0 or seg_end <= seg_start:
            continue
        raw = str(seg.get("text", "")).strip()
        if not raw:
            continue
        for cue_start, cue_end, piece in _chunk_caption(
            raw, max(0.0, seg_start), seg_end
        ):
            text = _escape_ass(piece)
            if not text:
                continue
            lines.append(
                f"Dialogue: 0,{_seconds_to_ass_time(cue_start)},"
                f"{_seconds_to_ass_time(cue_end)},Default,,0,0,0,,{text}"
            )
    return header + "\n".join(lines) + "\n"


def _build_filtergraph(
    *,
    mode: str,
    reframe_offset: float,
    subtitles_path: str | None,
    broll: Sequence[dict[str, Any]] = (),
) -> str:
    """Build the ffmpeg ``-filter_complex`` graph producing label ``[v]``.

    ``mode="crop"``   - scale to cover 1080x1920 then centre-crop (talking heads).
                        ``reframe_offset`` (0..1) shifts the horizontal window.
    ``mode="fit"``    - scale to fit inside 1080x1920 over a blurred, filled copy
                        of the frame (screen recordings, slides - nothing is lost).

    ``broll`` items are ``{"start", "end"}`` (clip-relative seconds); each maps to
    ffmpeg input index ``i + 1`` and is overlaid full-frame for its window.
    """
    w, h = TARGET_WIDTH, TARGET_HEIGHT
    if mode == "fit":
        # Cheap blur: cover-crop, shrink to ~1/12, scale back up. The upscale
        # interpolation does the blurring - orders of magnitude faster than gblur.
        graph = (
            f"[0:v]split=2[bg][fg];"
            f"[bg]scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h},scale={w // 12}:{h // 12},scale={w}:{h},"
            f"eq=brightness=-0.06,setsar=1[bg2];"
            f"[fg]scale={w}:{h}:force_original_aspect_ratio=decrease:"
            f"force_divisible_by=2,setsar=1[fg2];"
            f"[bg2][fg2]overlay=(W-w)/2:(H-h)/2[base]"
        )
    else:  # "crop"
        offset = min(1.0, max(0.0, reframe_offset))
        graph = (
            f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase:"
            f"force_divisible_by=2,"
            f"crop={w}:{h}:(iw-{w})*{offset:.3f}:(ih-{h})/2,setsar=1[base]"
        )

    tail = "[base]"
    for i, cut in enumerate(broll):
        s, e = float(cut["start"]), float(cut["end"])
        dur = max(0.1, e - s)
        graph += (
            f";[{i + 1}:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h},setsar=1,trim=duration={dur:.3f},"
            f"setpts=PTS-STARTPTS+{s:.3f}/TB[br{i}]"
        )
        graph += (
            f";{tail}[br{i}]overlay=0:0:eof_action=pass:"
            f"enable='between(t\\,{s:.3f}\\,{e:.3f})'[ov{i}]"
        )
        tail = f"[ov{i}]"

    if subtitles_path:
        escaped = (
            subtitles_path.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
        )
        graph += f";{tail}subtitles='{escaped}'[subbed]"
        tail = "[subbed]"
    graph += f";{tail}format=yuv420p[v]"
    return graph


def _build_ffmpeg_command(
    *,
    ffmpeg: str,
    source_path: str,
    start: float,
    duration: float,
    subtitles_path: str | None,
    output_path: str,
    reframe_offset: float = 0.5,
    mode: str = "fit",
    broll: Sequence[dict[str, Any]] = (),
) -> list[str]:
    """Build the FFmpeg argv for a single vertical clip render."""
    graph = _build_filtergraph(
        mode=mode,
        reframe_offset=reframe_offset,
        subtitles_path=subtitles_path,
        broll=broll,
    )
    cmd = [ffmpeg, "-y", "-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", source_path]
    for cut in broll:
        span = max(0.2, float(cut["end"]) - float(cut["start"]))
        # Only decode the slice we need from each stock clip.
        cmd += ["-t", f"{span + 0.3:.3f}", "-i", str(cut["path"])]
    cmd += [
        "-filter_complex",
        graph,
        "-map",
        "[v]",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        settings.FFMPEG_PRESET,
        "-crf",
        "23",
        "-profile:v",
        "high",
        "-pix_fmt",
        "yuv420p",
        "-fps_mode",
        "cfr",
        "-r",
        "30",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        # Hard cap on output length - a defensive wall against any filtergraph
        # (b-roll PTS shifts, overlay eof handling) that would run past the clip.
        "-t",
        f"{duration:.3f}",
        output_path,
    ]
    return cmd


def render_clip(
    source_key: str,
    start: float,
    end: float,
    caption_segments: Sequence[dict[str, Any]] | None,
    style: dict[str, Any] | None,
    *,
    project_id: int,
    clip_id: int,
) -> str:
    """Render a single vertical clip and upload it to storage.

    Args:
        source_key: Storage key of the project's source video.
        start: Clip start in seconds (absolute, within the source).
        end: Clip end in seconds.
        caption_segments: Timed caption entries ``[{start, end, text}]`` in
            absolute source time.
        style: Optional caption style overrides.
        project_id: Owning project id (for the output key).
        clip_id: Clip id (for the output key).

    Returns:
        The storage key of the rendered MP4.

    Raises:
        RenderingError: If FFmpeg is missing or the render fails.
        ValueError: If the time range is invalid.
    """
    if end <= start:
        raise ValueError("Clip end must be after start")

    ffmpeg = _ensure_ffmpeg()
    duration = end - start
    workdir = tempfile.mkdtemp(prefix="segmently-render-", dir=_work_root())
    try:
        source_path = os.path.join(workdir, "source")
        storage.download_file(source_key, source_path)

        subtitles_path: str | None = None
        if caption_segments:
            subtitles_path = os.path.join(workdir, "captions.ass")
            with open(subtitles_path, "w", encoding="utf-8") as fh:
                fh.write(_build_ass_subtitles(caption_segments, start, style))

        try:
            reframe_offset = float((style or {}).get("reframe_offset", 0.5))
        except (TypeError, ValueError):
            reframe_offset = 0.5

        mode = str((style or {}).get("render_mode", settings.RENDER_MODE)).lower()
        if mode not in ("fit", "crop"):
            mode = "fit"

        broll = _plan_broll(caption_segments, start, end, style, workdir)

        output_path = os.path.join(workdir, "clip.mp4")
        cmd = _build_ffmpeg_command(
            ffmpeg=ffmpeg,
            source_path=source_path,
            start=start,
            duration=duration,
            subtitles_path=subtitles_path,
            output_path=output_path,
            reframe_offset=reframe_offset,
            mode=mode,
            broll=broll,
        )
        logger.info("Running FFmpeg: %s", " ".join(cmd))
        proc = subprocess.run(  # noqa: S603 - args are constructed, not shell
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0 or not os.path.exists(output_path):
            logger.error("FFmpeg failed (%s): %s", proc.returncode, proc.stderr[-2000:])
            raise RenderingError(f"FFmpeg exited {proc.returncode}")

        out_key = clip_key(project_id, clip_id)
        storage.upload_file(output_path, out_key, content_type="video/mp4")
        return out_key
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _work_root() -> str:
    root = settings.MEDIA_WORK_DIR
    try:
        os.makedirs(root, exist_ok=True)
        return root
    except OSError:  # pragma: no cover - fall back to system temp
        return tempfile.gettempdir()
