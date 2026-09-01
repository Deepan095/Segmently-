"""Automatic B-roll: pick moments in a clip and drop in relevant stock footage.

The LLM chooses a few short, visual moments and a search phrase for each; the
phrase is looked up on the Pexels video API and the best portrait/HD result is
downloaded. The renderer overlays each file full-frame for its window while the
original audio and captions keep playing.

All times returned by :func:`plan_broll` / :func:`build_broll_overlays` are
**relative to the start of the clip** (0 = first frame of the clip).
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from typing import Any, TypedDict

from app.config import settings

logger = logging.getLogger("segmently.services.broll")

_PEXELS_SEARCH = "https://api.pexels.com/videos/search"
_MAX_FILE_BYTES = 60 * 1024 * 1024


class BrollCue(TypedDict):
    start: float
    end: float
    query: str


class BrollOverlay(TypedDict):
    start: float
    end: float
    path: str
    query: str


def _system_prompt(max_cues: int) -> str:
    return (
        "You add B-roll to a short vertical video. Given the clip's captions "
        "with timestamps (seconds from the clip start), choose up to "
        f"{max_cues} short moments to cover with stock footage.\n"
        "Rules:\n"
        f"- each moment is {settings.BROLL_MIN_SECONDS:.0f}-"
        f"{settings.BROLL_MAX_SECONDS:.0f} seconds long\n"
        "- only over words that describe something concrete and visual "
        "(an object, place, action, product, concept you can show)\n"
        "- never over the first 2 seconds or the last 2 seconds of the clip\n"
        "- moments must not overlap each other\n"
        "- 'query' is a plain-English stock-footage search phrase, 2-5 words, "
        "in English, e.g. 'person typing on laptop', 'city skyline sunset', "
        "'team meeting office', 'robot arm factory'\n\n"
        'Reply with ONLY JSON: {"cues":[{"start":<sec>,"end":<sec>,"query":<str>}]}'
    )


def _caption_lines(caption_segments: list[dict[str, Any]], clip_start: float) -> str:
    out = []
    for seg in caption_segments:
        text = str(seg.get("text", "")).strip()
        if not text:
            continue
        s = float(seg.get("start", 0.0)) - clip_start
        e = float(seg.get("end", 0.0)) - clip_start
        out.append(f"[{s:.1f} - {e:.1f}] {text}")
    return "\n".join(out)


def _extract_json(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", raw, re.DOTALL)
    if fence:
        raw = fence.group(1).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    raise ValueError("Could not parse JSON from B-roll response")


def plan_broll(
    caption_segments: list[dict[str, Any]],
    clip_start: float,
    clip_end: float,
) -> list[BrollCue]:
    """Ask the LLM for non-overlapping, in-bounds B-roll cues (clip-relative)."""
    if not settings.OPENAI_API_KEY:
        return []
    body = _caption_lines(caption_segments, clip_start)
    if not body:
        return []

    try:
        import openai
    except ImportError:  # pragma: no cover
        return []

    duration = clip_end - clip_start
    max_cues = max(1, int(settings.BROLL_MAX_PER_CLIP))
    try:
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        completion = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            max_tokens=700,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _system_prompt(max_cues)},
                {
                    "role": "user",
                    "content": f"Clip is {duration:.0f}s long.\n\nCAPTIONS:\n{body}",
                },
            ],
        )
        payload = _extract_json(completion.choices[0].message.content or "")
    except Exception:  # noqa: BLE001 - b-roll is best-effort, never fail a render
        logger.exception("plan_broll failed")
        return []

    rows = payload.get("cues")
    if not isinstance(rows, list):
        return []

    lo, hi = settings.BROLL_MIN_SECONDS, settings.BROLL_MAX_SECONDS
    budget = duration * float(settings.BROLL_MAX_COVERAGE)
    cues: list[BrollCue] = []
    used = 0.0
    for row in sorted(rows, key=lambda r: _safe_float(r.get("start"))):
        s = _safe_float(row.get("start"))
        e = _safe_float(row.get("end"))
        query = str(row.get("query") or "").strip()
        if not query or e <= s:
            continue
        s = max(2.0, s)
        e = min(duration - 2.0, e)
        span = e - s
        if span < lo:
            continue
        if span > hi:
            e = s + hi
            span = hi
        if cues and s < cues[-1]["end"] + 0.2:  # overlap / too close
            continue
        if used + span > budget:
            continue
        cues.append({"start": round(s, 2), "end": round(e, 2), "query": query})
        used += span
        if len(cues) >= max_cues:
            break
    return cues


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def fetch_stock_video(query: str, dest_dir: str) -> str | None:
    """Download one portrait HD stock clip for *query*. Returns a path or None."""
    if not settings.PEXELS_API_KEY:
        return None
    try:
        import httpx
    except ImportError:  # pragma: no cover
        return None

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                _PEXELS_SEARCH,
                params={"query": query, "per_page": 8, "orientation": "portrait", "size": "medium"},
                headers={"Authorization": settings.PEXELS_API_KEY},
            )
            resp.raise_for_status()
            videos = resp.json().get("videos") or []
            file_url = _pick_file(videos)
            if not file_url:
                return None
            dest = os.path.join(dest_dir, f"broll-{abs(hash(query)) % 10**8}.mp4")
            written = 0
            with client.stream("GET", file_url) as media, open(dest, "wb") as fh:
                media.raise_for_status()
                for chunk in media.iter_bytes(1 << 20):
                    written += len(chunk)
                    if written > _MAX_FILE_BYTES:
                        raise ValueError("stock clip too large")
                    fh.write(chunk)
        logger.info("Fetched B-roll for %r (%d bytes)", query, written)
        return dest
    except Exception:  # noqa: BLE001 - best-effort
        logger.warning("fetch_stock_video failed for %r", query, exc_info=True)
        return None


def _pick_file(videos: list[dict[str, Any]]) -> str | None:
    """Choose the smallest video file that is at least 720px on the short side."""
    best: tuple[int, str] | None = None
    for video in videos:
        for f in video.get("video_files") or []:
            link = f.get("link")
            w, h = f.get("width") or 0, f.get("height") or 0
            if not link or min(w, h) < 700 or min(w, h) > 1500:
                continue
            area = w * h
            if best is None or area < best[0]:
                best = (area, link)
    return best[1] if best else None


def build_broll_overlays(
    caption_segments: list[dict[str, Any]],
    clip_start: float,
    clip_end: float,
    workdir: str,
) -> list[BrollOverlay]:
    """Plan cues and download a stock clip for each. Missing downloads are skipped."""
    overlays: list[BrollOverlay] = []
    for cue in plan_broll(caption_segments, clip_start, clip_end):
        path = fetch_stock_video(cue["query"], workdir)
        if path:
            overlays.append(
                {
                    "start": cue["start"],
                    "end": cue["end"],
                    "path": path,
                    "query": cue["query"],
                }
            )
    return overlays


def _tmpdir() -> str:  # pragma: no cover - convenience for ad-hoc use
    return tempfile.mkdtemp(prefix="segmently-broll-")
