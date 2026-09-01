"""Speech-to-text transcription behind a small interface.

The pipeline calls :func:`transcribe` with a local file path. Two backends are
available, chosen by ``settings.TRANSCRIPTION_BACKEND``:

* ``"local"`` (default) - ``faster-whisper`` (CTranslate2), runs on the worker
  CPU. The model is loaded once per process and reused.
* ``"openai"`` - the OpenAI audio transcription API (``whisper-1``). Much faster
  than local CPU inference; audio is extracted with ffmpeg and sent as a small
  compressed file. Needs ``OPENAI_API_KEY``.

Return shape::

    {
        "language": "en",
        "full_text": "...",
        "segments": [{"start": 0.0, "end": 4.2, "text": "..."}, ...],
    }
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from functools import lru_cache
from typing import Any, TypedDict

from app.config import settings

logger = logging.getLogger("segmently.services.transcription")

# OpenAI's audio endpoint rejects files larger than 25 MB.
_OPENAI_MAX_AUDIO_BYTES = 25 * 1024 * 1024


class TranscriptSegment(TypedDict):
    start: float
    end: float
    text: str


class TranscriptionResult(TypedDict):
    language: str | None
    full_text: str
    segments: list[TranscriptSegment]


class TranscriptionUnavailable(RuntimeError):
    """Raised when no transcription backend is installed/available."""


# --- local: faster-whisper ---------------------------------------------------

@lru_cache(maxsize=2)
def _load_faster_whisper(model: str, device: str, compute_type: str) -> Any:
    """Load (and cache for the process lifetime) a faster-whisper model."""
    from faster_whisper import WhisperModel  # type: ignore[import-not-found]

    logger.info("Loading faster-whisper model %s (%s/%s)", model, device, compute_type)
    return WhisperModel(model, device=device, compute_type=compute_type)


def _transcribe_faster_whisper(path: str) -> TranscriptionResult:
    model = _load_faster_whisper(
        settings.WHISPER_MODEL, settings.WHISPER_DEVICE, settings.WHISPER_COMPUTE_TYPE
    )
    segments_iter, info = model.transcribe(path, vad_filter=True)
    segments: list[TranscriptSegment] = []
    parts: list[str] = []
    for seg in segments_iter:
        text = seg.text.strip()
        segments.append({"start": float(seg.start), "end": float(seg.end), "text": text})
        parts.append(text)
    return {
        "language": getattr(info, "language", None),
        "full_text": " ".join(parts).strip(),
        "segments": segments,
    }


# --- openai audio API ------------------------------------------------------

def _extract_audio(path: str) -> str:
    """Extract a small mono 16 kHz Opus track from *path* for API upload."""
    out = tempfile.mkstemp(prefix="segmently-audio-", suffix=".ogg")[1]
    cmd = [
        settings.FFMPEG_BINARY, "-y", "-i", path,
        "-vn", "-ac", "1", "-ar", "16000",
        "-c:a", "libopus", "-b:a", "16k",
        out,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not os.path.exists(out):
        raise RuntimeError(f"ffmpeg audio extraction failed: {proc.stderr[-500:]}")
    return out


def _transcribe_openai(path: str) -> TranscriptionResult:
    if not settings.OPENAI_API_KEY:
        raise TranscriptionUnavailable(
            "TRANSCRIPTION_BACKEND=openai but OPENAI_API_KEY is not set."
        )
    import openai

    audio_path = _extract_audio(path)
    try:
        size = os.path.getsize(audio_path)
        if size > _OPENAI_MAX_AUDIO_BYTES:
            raise RuntimeError(
                f"Extracted audio is {size / 1e6:.1f} MB, over the 25 MB API "
                "limit. Use the 'local' transcription backend for this source."
            )
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        with open(audio_path, "rb") as fh:
            resp = client.audio.transcriptions.create(
                model=settings.OPENAI_TRANSCRIBE_MODEL,
                file=fh,
                response_format="verbose_json",
            )
    finally:
        try:
            os.remove(audio_path)
        except OSError:
            pass

    raw_segments = getattr(resp, "segments", None) or []
    segments: list[TranscriptSegment] = [
        {
            "start": float(getattr(s, "start", 0.0)),
            "end": float(getattr(s, "end", 0.0)),
            "text": str(getattr(s, "text", "")).strip(),
        }
        for s in raw_segments
    ]
    return {
        "language": getattr(resp, "language", None),
        "full_text": str(getattr(resp, "text", "")).strip(),
        "segments": segments,
    }


# --- entrypoint --------------------------------------------------------------

def transcribe(path_or_key: str) -> TranscriptionResult:
    """Transcribe an audio/video file at a local *path*.

    Raises:
        TranscriptionUnavailable: If the selected backend is not usable.
        FileNotFoundError: If *path_or_key* does not exist on disk.
    """
    if not os.path.exists(path_or_key):
        raise FileNotFoundError(
            f"transcribe() expects a local file path, got: {path_or_key!r}"
        )

    backend = settings.TRANSCRIPTION_BACKEND.lower()
    logger.info("Transcribing %s with backend=%s", path_or_key, backend)

    if backend == "openai":
        try:
            return _transcribe_openai(path_or_key)
        except ImportError as exc:
            raise TranscriptionUnavailable("The 'openai' package is not installed.") from exc

    # backend == "local" (default)
    try:
        return _transcribe_faster_whisper(path_or_key)
    except ImportError as exc:
        raise TranscriptionUnavailable(
            "faster-whisper is not installed in the worker image. Set "
            "TRANSCRIPTION_BACKEND=openai to use the OpenAI audio API instead."
        ) from exc
