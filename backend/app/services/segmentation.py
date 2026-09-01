"""LLM segment detection: pick self-contained ~1-minute moments from a transcript.

Long videos are split into time windows so clips are spread across the whole
source (not just clustered near the start), then each candidate's start/end is
snapped to real transcript-segment boundaries so a clip never begins or ends
mid-sentence. Uses the OpenAI Chat Completions API in JSON mode.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, TypedDict

from app.config import settings

logger = logging.getLogger("segmently.services.segmentation")

# Duration envelope for a finished clip.
MIN_SEGMENT_SECONDS = 25.0
MAX_SEGMENT_SECONDS = 95.0
TARGET_MIN_SECONDS = 45.0
TARGET_MAX_SECONDS = 75.0
TARGET_SECONDS = 60.0

# How far a model-proposed boundary may be nudged to land on a sentence edge.
_SNAP_TOLERANCE_SECONDS = 6.0


class DetectedSegment(TypedDict):
    start: float
    end: float
    title: str
    score: int
    score_reason: str


class SegmentationUnavailable(RuntimeError):
    """Raised when the OpenAI API key or SDK is not available."""


def _system_prompt(clips_wanted: int) -> str:
    return (
        "You are a short-form video editor. From a timestamped transcript you "
        "select the moments that work best as standalone ~1-minute vertical "
        "clips (Shorts / Reels / TikTok).\n\n"
        f"Select {clips_wanted} clips from THIS portion of the transcript. "
        "Every clip MUST:\n"
        f"- run about {int(TARGET_SECONDS)} seconds "
        f"({int(TARGET_MIN_SECONDS)}-{int(TARGET_MAX_SECONDS)}s)\n"
        "- be a COMPLETE thought: it starts exactly where the speaker begins a "
        "point and ends where they finish it. Never cut in mid-sentence or "
        "mid-explanation.\n"
        "- make full sense to someone who has not seen the rest of the video "
        "(no dangling 'as I said', no unresolved setup)\n"
        "- open with a hook and deliver a payoff, lesson, story or strong claim\n"
        "- not overlap another clip you selected\n\n"
        "Set start/end to timestamps that appear in the transcript. Give each "
        "clip a punchy title (<=70 chars), an integer score 0-100 for how well "
        "it will perform as a short, and a one-sentence score_reason.\n\n"
        'Reply with ONLY JSON: {"segments":[{"start":<sec>,"end":<sec>,'
        '"title":<str>,"score":<int>,"score_reason":<str>}]}'
    )


def _format_lines(segments: list[dict[str, Any]]) -> str:
    lines = []
    for seg in segments:
        text = str(seg.get("text", "")).strip()
        if text:
            lines.append(
                f"[{float(seg.get('start', 0.0)):.1f} - "
                f"{float(seg.get('end', 0.0)):.1f}] {text}"
            )
    return "\n".join(lines)


def _extract_json(raw: str) -> dict[str, Any]:
    """Best-effort parse of a JSON object from an LLM response."""
    raw = raw.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", raw, re.DOTALL)
    if fence:
        raw = fence.group(1).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise ValueError("Could not parse JSON from segmentation response")


def _snap_to_boundaries(
    start: float, end: float, tx_segments: list[dict[str, Any]]
) -> tuple[float, float] | None:
    """Expand/shift ``[start, end]`` onto transcript-segment edges.

    The clip is grown to whole transcript segments so it never begins or ends
    part-way through a sentence, then trimmed/extended toward the target length.
    Returns ``None`` if no transcript segments fall in range.
    """
    if not tx_segments:
        return None

    starts = [float(s.get("start", 0.0)) for s in tx_segments]
    ends = [float(s.get("end", 0.0)) for s in tx_segments]

    # First segment whose end is past the requested start.
    lo = next((i for i, e in enumerate(ends) if e > start + 0.01), None)
    # Last segment whose start is before the requested end.
    hi = next(
        (i for i in range(len(starts) - 1, -1, -1) if starts[i] < end - 0.01),
        None,
    )
    if lo is None or hi is None or hi < lo:
        return None

    # If the model's start sits well inside a segment, keep that segment.
    if start - starts[lo] > _SNAP_TOLERANCE_SECONDS and lo + 1 <= hi:
        lo += 1

    new_start, new_end = starts[lo], ends[hi]

    # Too short -> pull in following segments until we reach the target minimum.
    j = hi
    while new_end - new_start < TARGET_MIN_SECONDS and j + 1 < len(tx_segments):
        j += 1
        new_end = ends[j]

    # Too long -> drop trailing segments while staying above the target minimum.
    while new_end - new_start > TARGET_MAX_SECONDS and hi > lo:
        hi -= 1
        if ends[hi] - new_start >= TARGET_MIN_SECONDS:
            new_end = ends[hi]
        else:
            new_end = min(new_end, new_start + TARGET_MAX_SECONDS)
            break

    duration = new_end - new_start
    if duration < MIN_SEGMENT_SECONDS or duration > MAX_SEGMENT_SECONDS:
        return None
    return round(new_start, 2), round(new_end, 2)


def _coerce_segments(
    payload: dict[str, Any], tx_segments: list[dict[str, Any]]
) -> list[DetectedSegment]:
    rows = payload.get("segments")
    if not isinstance(rows, list):
        raise ValueError("Segmentation payload missing 'segments' list")

    out: list[DetectedSegment] = []
    for row in rows:
        try:
            raw_start = max(0.0, float(row["start"]))
            raw_end = float(row["end"])
        except (KeyError, TypeError, ValueError):
            logger.warning("Skipping malformed segment: %s", row)
            continue
        if raw_end <= raw_start:
            continue

        snapped = _snap_to_boundaries(raw_start, raw_end, tx_segments)
        if snapped is None:
            logger.info("Dropping segment that would not resolve to a clean clip")
            continue
        start, end = snapped

        try:
            score = max(0, min(100, int(round(float(row.get("score", 0))))))
        except (TypeError, ValueError):
            score = 0
        out.append(
            {
                "start": start,
                "end": end,
                "title": str(row.get("title") or "Untitled moment")[:255],
                "score": score,
                "score_reason": str(row.get("score_reason") or "").strip(),
            }
        )
    return out


def _dedupe_overlaps(segments: list[DetectedSegment]) -> list[DetectedSegment]:
    """Keep the higher-scoring clip when two clips overlap substantially."""
    chosen: list[DetectedSegment] = []
    for seg in sorted(segments, key=lambda s: s["score"], reverse=True):
        overlaps = False
        for kept in chosen:
            latest_start = max(seg["start"], kept["start"])
            earliest_end = min(seg["end"], kept["end"])
            overlap = max(0.0, earliest_end - latest_start)
            if overlap > 0.2 * min(
                seg["end"] - seg["start"], kept["end"] - kept["start"]
            ):
                overlaps = True
                break
        if not overlaps:
            chosen.append(seg)
    return chosen


def _windows(
    tx_segments: list[dict[str, Any]], total: float
) -> list[list[dict[str, Any]]]:
    """Split the transcript into time windows for spread-out clip selection."""
    win = float(settings.SEGMENT_WINDOW_SECONDS)
    if total <= win * 1.4:
        return [tx_segments]
    count = max(2, round(total / win))
    span = total / count
    buckets: list[list[dict[str, Any]]] = [[] for _ in range(count)]
    for seg in tx_segments:
        idx = min(count - 1, int(float(seg.get("start", 0.0)) // span))
        buckets[idx].append(seg)
    return [b for b in buckets if b]


def detect_segments(transcript: dict[str, Any]) -> list[DetectedSegment]:
    """Detect the best short-form moments in *transcript*.

    Returns a score-sorted list of :class:`DetectedSegment`. Raises
    :class:`SegmentationUnavailable` if the OpenAI key/SDK is missing.
    """
    if not settings.OPENAI_API_KEY:
        raise SegmentationUnavailable(
            "OPENAI_API_KEY is not configured - cannot run segment detection."
        )
    try:
        import openai
    except ImportError as exc:  # pragma: no cover - dependency missing
        raise SegmentationUnavailable("The 'openai' package is not installed.") from exc

    tx_segments = [
        s for s in (transcript.get("segments") or []) if str(s.get("text", "")).strip()
    ]
    if not tx_segments:
        logger.warning("Transcript has no usable segments")
        return []

    total = max(float(s.get("end", 0.0)) for s in tx_segments)
    windows = _windows(tx_segments, total)
    target_total = int(settings.SEGMENTS_TARGET)
    per_window = max(1, round(target_total / len(windows)))
    language = transcript.get("language") or "unknown"

    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    candidates: list[DetectedSegment] = []

    for i, window in enumerate(windows):
        body = _format_lines(window)
        if not body:
            continue
        want = per_window if len(windows) > 1 else target_total
        user = (
            f"Transcript language: {language}. This is part {i + 1} of "
            f"{len(windows)} of a video that is {total / 60:.0f} minutes long.\n"
            f"Pick {want} clip(s) from the transcript below.\n\nTRANSCRIPT:\n{body}"
        )
        try:
            completion = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                max_tokens=2000,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": _system_prompt(want)},
                    {"role": "user", "content": user},
                ],
            )
            text = completion.choices[0].message.content or ""
            logger.info("Segmentation window %d/%d -> %d chars", i + 1, len(windows), len(text))
            candidates.extend(_coerce_segments(_extract_json(text), window))
        except Exception:  # noqa: BLE001 - one bad window must not fail the clip
            logger.exception("Segmentation failed for window %d", i + 1)

    ranked = _dedupe_overlaps(candidates)
    ranked.sort(key=lambda s: s["score"], reverse=True)
    result = ranked[: int(settings.SEGMENTS_MAX)]
    result.sort(key=lambda s: s["start"])
    logger.info(
        "Segmentation produced %d clips from %d candidates across %d windows",
        len(result), len(candidates), len(windows),
    )
    return result
