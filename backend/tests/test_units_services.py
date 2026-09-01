"""Unit tests for the external-service wrapper modules.

These exercise the *real* implementations (the autouse fakes in conftest only
patch the boto3 client factory and the high-level pipeline entry points; the
originals of the patched entry points are captured here at import time).
"""

from __future__ import annotations

import subprocess
import sys
import types

import pytest

import app.services.broll as broll
import app.services.rendering as rendering
import app.services.segmentation as segmentation
import app.services.storage as storage
import app.services.transcription as transcription

# Captured before the autouse fixture rebinds the module attributes.
_REAL_DETECT = segmentation.detect_segments
_REAL_RENDER = rendering.render_clip
_REAL_TRANSCRIBE = transcription.transcribe


# --------------------------------------------------------------------------- #
# storage.py
# --------------------------------------------------------------------------- #
def test_storage_roundtrip(tmp_path):
    storage.put_object("k/a.txt", b"hello", content_type="text/plain")
    assert storage.object_exists("k/a.txt")

    dest = tmp_path / "out.bin"
    storage.download_file("k/a.txt", str(dest))
    assert dest.read_bytes() == b"hello"

    src = tmp_path / "in.bin"
    src.write_bytes(b"xyz")
    storage.upload_file(str(src), "k/b.txt")
    assert storage.object_exists("k/b.txt")

    body = storage.get_object_stream("k/a.txt")
    assert body.read() == b"hello"

    storage.delete_key("k/a.txt")
    assert storage.object_exists("nope/missing.txt") is False


def test_storage_delete_prefix_counts():
    storage.put_object("projects/9/source.mp4", b"1")
    storage.put_object("projects/9/clips/1.mp4", b"2")
    removed = storage.delete_prefix("projects/9/")
    assert removed == 2


def test_storage_presigned_urls():
    assert storage.generate_presigned_get("k.mp4", 60).startswith("https://signed.test/get_object/")
    assert storage.generate_presigned_put("k.mp4", 60, content_type="video/mp4").startswith(
        "https://signed.test/put_object/"
    )


def test_storage_wraps_client_errors(monkeypatch):
    class Boom:
        def put_object(self, **kw):
            raise ValueError("kaboom")

    monkeypatch.setattr("app.services.storage.get_client", lambda: Boom())
    with pytest.raises(storage.StorageError):
        storage.put_object("k", b"x")


# --------------------------------------------------------------------------- #
# segmentation.py
# --------------------------------------------------------------------------- #
def test_extract_json_plain_and_fenced():
    assert segmentation._extract_json('{"a": 1}') == {"a": 1}
    assert segmentation._extract_json('```json\n{"a": 2}\n```') == {"a": 2}
    assert segmentation._extract_json('noise {"a": 3} trailing') == {"a": 3}
    with pytest.raises(ValueError):
        segmentation._extract_json("not json at all")


def _tx(n_lines=14, step=5.0):
    """A synthetic transcript: n_lines sentences of `step` seconds each."""
    return [
        {"start": i * step, "end": (i + 1) * step, "text": f"sentence {i}."}
        for i in range(n_lines)
    ]


def test_coerce_segments_snaps_and_clamps():
    tx = _tx()  # 14 lines x 5s = 70s total
    payload = {
        "segments": [
            {"start": 2, "end": 52, "title": "ok", "score": 150, "score_reason": "r"},
            {"start": 3, "end": 5, "title": "too short -> extended", "score": 40},
            {"start": 5, "end": 5, "title": "zero", "score": 10},
            {"start": "bad", "end": 10, "title": "malformed", "score": 10},
        ]
    }
    out = segmentation._coerce_segments(payload, tx)
    # first two survive (snapped/extended onto sentence edges); score clamped
    assert len(out) == 2
    assert out[0]["score"] == 100
    # boundaries land exactly on transcript-segment edges (multiples of 5s)
    for seg in out:
        assert seg["start"] % 5 == 0 and seg["end"] % 5 == 0
        assert 25.0 <= seg["end"] - seg["start"] <= 95.0

    with pytest.raises(ValueError):
        segmentation._coerce_segments({"nope": []}, tx)


def test_format_lines_and_system_prompt():
    body = segmentation._format_lines([{"start": 0, "end": 1, "text": "hi"}])
    assert "[0.0 - 1.0] hi" in body
    assert "5" in segmentation._system_prompt(5)


def test_windows_split_long_transcript(monkeypatch):
    monkeypatch.setattr(segmentation.settings, "SEGMENT_WINDOW_SECONDS", 600)
    short = segmentation._windows(_tx(4), total=20.0)
    assert len(short) == 1
    long_tx = [
        {"start": i * 60.0, "end": i * 60.0 + 55, "text": f"s{i}"} for i in range(60)
    ]  # ~1 hour
    wins = segmentation._windows(long_tx, total=3600.0)
    assert len(wins) >= 5


def test_detect_segments_without_api_key(monkeypatch):
    monkeypatch.setattr(segmentation.settings, "OPENAI_API_KEY", "")
    with pytest.raises(segmentation.SegmentationUnavailable):
        _REAL_DETECT({"segments": []})


def test_detect_segments_with_fake_openai(monkeypatch):
    monkeypatch.setattr(segmentation.settings, "OPENAI_API_KEY", "sk-test")

    response = (
        '{"segments": [{"start": 0, "end": 50, "title": "Hook", '
        '"score": 88, "score_reason": "great"}]}'
    )

    fake = types.ModuleType("openai")

    class _Completions:
        def create(self, **kwargs):
            message = types.SimpleNamespace(content=response)
            choice = types.SimpleNamespace(message=message)
            return types.SimpleNamespace(choices=[choice])

    class OpenAI:  # noqa: N801
        def __init__(self, api_key=None):
            self.chat = types.SimpleNamespace(completions=_Completions())

    fake.OpenAI = OpenAI
    monkeypatch.setitem(sys.modules, "openai", fake)

    out = _REAL_DETECT({"language": "en", "segments": [{"start": 0, "end": 50, "text": "x"}]})
    assert out[0]["title"] == "Hook"
    assert out[0]["score"] == 88


# --------------------------------------------------------------------------- #
# rendering.py
# --------------------------------------------------------------------------- #
def test_ass_time_and_escape():
    assert rendering._seconds_to_ass_time(3661.5) == "1:01:01.50"
    assert rendering._seconds_to_ass_time(-5) == "0:00:00.00"
    assert rendering._escape_ass("a{b}c\nd") == "a(b)c d"


def test_build_ass_subtitles_rebases_times():
    doc = rendering._build_ass_subtitles(
        [{"start": 65.0, "end": 70.0, "text": "hello"}, {"start": 0, "end": 0, "text": "skip"}],
        clip_start=60.0,
        style={"font_size": 40},
    )
    assert "Dialogue: 0,0:00:05.00,0:00:10.00" in doc
    assert "hello" in doc


def test_build_ffmpeg_command_fit_mode_default():
    cmd = rendering._build_ffmpeg_command(
        ffmpeg="ffmpeg",
        source_path="/s.mp4",
        start=1.0,
        duration=30.0,
        subtitles_path="/tmp/c.ass",
        output_path="/o.mp4",
    )
    joined = " ".join(cmd)
    assert cmd[0] == "ffmpeg"
    assert "-filter_complex" in cmd
    assert "subtitles=" in joined
    # fit mode: filled/blurred background split + fitted foreground overlay
    assert "split=2[bg][fg]" in joined
    assert "overlay=" in joined
    assert "force_original_aspect_ratio=decrease" in joined
    assert cmd[-1] == "/o.mp4"


def test_build_ffmpeg_command_crop_mode():
    cmd = rendering._build_ffmpeg_command(
        ffmpeg="ffmpeg",
        source_path="/s.mp4",
        start=1.0,
        duration=30.0,
        subtitles_path=None,
        output_path="/o.mp4",
        reframe_offset=0.25,
        mode="crop",
    )
    joined = " ".join(cmd)
    assert "crop=1080:1920:(iw-1080)*0.250" in joined
    assert "split=2[bg][fg]" not in joined  # no background fill in crop mode


def test_build_ffmpeg_command_with_broll():
    cmd = rendering._build_ffmpeg_command(
        ffmpeg="ffmpeg",
        source_path="/s.mp4",
        start=1.0,
        duration=30.0,
        subtitles_path="/c.ass",
        output_path="/o.mp4",
        mode="crop",
        broll=[
            {"start": 5.0, "end": 9.0, "path": "/b0.mp4"},
            {"start": 15.0, "end": 19.0, "path": "/b1.mp4"},
        ],
    )
    joined = " ".join(cmd)
    # two extra inputs, gated overlays, subtitles still on top
    assert cmd.count("-i") == 3
    assert "/b0.mp4" in cmd and "/b1.mp4" in cmd
    assert "enable='between(t\\,5.000\\,9.000)'" in joined
    assert joined.index("overlay") < joined.index("subtitles=")


# --------------------------------------------------------------------------- #
# broll.py
# --------------------------------------------------------------------------- #
def _caps():
    return [
        {"start": 0.0, "end": 4.0, "text": "we built a robot arm for the factory"},
        {"start": 4.0, "end": 9.0, "text": "it welds car doors all day long"},
        {"start": 9.0, "end": 14.0, "text": "and it never misses a beat"},
    ]


def test_plan_broll_bounds_and_budget(monkeypatch):
    monkeypatch.setattr(broll.settings, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(broll.settings, "BROLL_MAX_PER_CLIP", 3)

    response = (
        '{"cues":[{"start":3,"end":7,"query":"robot arm factory"},'
        '{"start":3.5,"end":6,"query":"overlapping - dropped"},'
        '{"start":10,"end":30,"query":"too long - clamped"}]}'
    )
    fake = types.ModuleType("openai")

    class _Completions:
        def create(self, **kw):
            msg = types.SimpleNamespace(content=response)
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])

    class OpenAI:  # noqa: N801
        def __init__(self, api_key=None):
            self.chat = types.SimpleNamespace(completions=_Completions())

    fake.OpenAI = OpenAI
    monkeypatch.setitem(sys.modules, "openai", fake)

    cues = broll.plan_broll(_caps(), clip_start=0.0, clip_end=14.0)
    assert 1 <= len(cues) <= 3
    for c in cues:
        assert c["start"] >= 2.0 and c["end"] <= 12.0
        assert broll.settings.BROLL_MIN_SECONDS <= c["end"] - c["start"] <= broll.settings.BROLL_MAX_SECONDS
    # cues never overlap
    for a, b in zip(cues, cues[1:]):
        assert a["end"] <= b["start"]


def test_plan_broll_no_key_returns_empty(monkeypatch):
    monkeypatch.setattr(broll.settings, "OPENAI_API_KEY", "")
    assert broll.plan_broll(_caps(), 0.0, 14.0) == []


def test_pick_file_prefers_smallest_hd():
    videos = [
        {"video_files": [
            {"link": "a", "width": 400, "height": 700},          # too small
            {"link": "b", "width": 1080, "height": 1920},         # ok, large
            {"link": "c", "width": 720, "height": 1280},          # ok, smaller
        ]},
    ]
    assert broll._pick_file(videos) == "c"
    assert broll._pick_file([]) is None


def test_render_clip_missing_ffmpeg(monkeypatch):
    monkeypatch.setattr("app.services.rendering.shutil.which", lambda b: None)
    with pytest.raises(rendering.RenderingError):
        _REAL_RENDER("src.mp4", 0.0, 10.0, [], None, project_id=1, clip_id=1)


def test_render_clip_happy_path(monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.rendering.shutil.which", lambda b: "/usr/bin/ffmpeg")
    storage.put_object("projects/1/source.mp4", b"video")

    def _fake_run(cmd, **kw):
        # cmd[-1] is the output path - create it so the success check passes.
        with open(cmd[-1], "wb") as fh:
            fh.write(b"rendered")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr("app.services.rendering.subprocess.run", _fake_run)

    out_key = _REAL_RENDER(
        "projects/1/source.mp4",
        0.0,
        10.0,
        [{"start": 0.0, "end": 2.0, "text": "hi"}],
        None,
        project_id=1,
        clip_id=7,
    )
    assert out_key == "projects/1/clips/7.mp4"


def test_render_clip_invalid_range():
    with pytest.raises(ValueError):
        _REAL_RENDER("s", 10.0, 5.0, [], None, project_id=1, clip_id=1)


# --------------------------------------------------------------------------- #
# transcription.py
# --------------------------------------------------------------------------- #
def test_transcribe_missing_file():
    with pytest.raises(FileNotFoundError):
        _REAL_TRANSCRIBE("/no/such/file.mp4")


@pytest.fixture(autouse=True)
def _clear_whisper_model_cache():
    transcription._load_faster_whisper.cache_clear()
    yield
    transcription._load_faster_whisper.cache_clear()


def test_transcribe_no_backend_available(tmp_path, monkeypatch):
    monkeypatch.setattr(transcription.settings, "TRANSCRIPTION_BACKEND", "local")
    media = tmp_path / "a.wav"
    media.write_bytes(b"x")
    with pytest.raises(transcription.TranscriptionUnavailable):
        _REAL_TRANSCRIBE(str(media))


def test_transcribe_uses_faster_whisper(monkeypatch, tmp_path):
    monkeypatch.setattr(transcription.settings, "TRANSCRIPTION_BACKEND", "local")
    media = tmp_path / "a.wav"
    media.write_bytes(b"x")

    fake = types.ModuleType("faster_whisper")

    class WhisperModel:  # noqa: N801
        def __init__(self, *a, **kw):
            pass

        def transcribe(self, path, vad_filter=True):
            seg = types.SimpleNamespace(start=0.0, end=1.5, text=" hello ")
            info = types.SimpleNamespace(language="en")
            return [seg], info

    fake.WhisperModel = WhisperModel
    monkeypatch.setitem(sys.modules, "faster_whisper", fake)

    result = _REAL_TRANSCRIBE(str(media))
    assert result["language"] == "en"
    assert result["full_text"] == "hello"
    assert result["segments"][0]["end"] == 1.5


def test_transcribe_openai_backend(monkeypatch, tmp_path):
    monkeypatch.setattr(transcription.settings, "TRANSCRIPTION_BACKEND", "openai")
    monkeypatch.setattr(transcription.settings, "OPENAI_API_KEY", "sk-test")
    media = tmp_path / "a.mp4"
    media.write_bytes(b"x")

    # ffmpeg audio extraction -> produce a tiny fake file at the temp path.
    def _fake_extract(path):
        p = tmp_path / "audio.ogg"
        p.write_bytes(b"OggS-fake")
        return str(p)

    monkeypatch.setattr(transcription, "_extract_audio", _fake_extract)

    fake = types.ModuleType("openai")

    class _Audio:
        def __init__(self):
            self.transcriptions = self

        def create(self, **kw):
            seg = types.SimpleNamespace(start=0.0, end=2.0, text=" hi there ")
            return types.SimpleNamespace(text="hi there", language="en", segments=[seg])

    class OpenAI:  # noqa: N801
        def __init__(self, api_key=None):
            self.audio = _Audio()

    fake.OpenAI = OpenAI
    monkeypatch.setitem(sys.modules, "openai", fake)

    result = _REAL_TRANSCRIBE(str(media))
    assert result["language"] == "en"
    assert result["full_text"] == "hi there"
    assert result["segments"][0]["end"] == 2.0
