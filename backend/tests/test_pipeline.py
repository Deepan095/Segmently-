"""Worker media pipeline: download -> transcribe -> segment -> render.

The arq task functions are invoked directly with a fake ``ctx``. All external
work (HTTP download, S3, Whisper, Anthropic, FFmpeg) is faked by the autouse
``_external_fakes`` fixture in conftest.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.models.clip import Clip, ClipStatus
from app.models.clip_caption import ClipCaption
from app.models.processing_job import JobStatus, JobType, ProcessingJob
from app.models.project import Project, ProjectStatus, SourceType
from app.models.transcript import Transcript
from app.workers import pipeline


@pytest.fixture
def ctx():
    return {"redis": AsyncMock()}


def _url_project(db, **kw):
    project = Project(
        user_id=kw["user_id"],
        title="P",
        source_type=SourceType.url,
        source_url="https://example.com/video.mp4",
        status=ProjectStatus.pending,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def _transcript(db, project_id):
    t = Transcript(
        project_id=project_id,
        language="en",
        full_text="hello world this is the transcript body",
        segments=[
            {"start": 0.0, "end": 60.0, "text": "hello world"},
            {"start": 60.0, "end": 120.0, "text": "this is the transcript body"},
        ],
    )
    db.add(t)
    db.commit()
    return t


async def test_run_download_stores_source_and_chains(ctx, db, auth_user):
    project = _url_project(db, user_id=auth_user.id)

    result = await pipeline.run_download(ctx, project.id)
    assert result

    db.expire_all()
    reloaded = db.get(Project, project.id)
    assert reloaded.storage_key is not None
    assert reloaded.file_size_bytes and reloaded.file_size_bytes > 0

    job = db.query(ProcessingJob).filter_by(project_id=project.id, job_type=JobType.download).one()
    assert job.status == JobStatus.completed
    assert job.progress_pct == 100
    ctx["redis"].enqueue_job.assert_awaited_with("run_transcribe", project.id)


async def test_run_transcribe_persists_transcript(ctx, db, auth_user):
    project = _url_project(db, user_id=auth_user.id)
    project.storage_key = "projects/1/source.mp4"
    db.commit()

    await pipeline.run_transcribe(ctx, project.id)

    db.expire_all()
    transcript = db.query(Transcript).filter_by(project_id=project.id).one()
    assert transcript.language == "en"
    assert len(transcript.segments) == 2
    job = db.query(ProcessingJob).filter_by(project_id=project.id, job_type=JobType.transcribe).one()
    assert job.status == JobStatus.completed
    ctx["redis"].enqueue_job.assert_awaited_with("run_segment", project.id)


async def test_run_segment_creates_clip_rows(ctx, db, auth_user):
    project = _url_project(db, user_id=auth_user.id)
    project.storage_key = "projects/1/source.mp4"
    db.commit()
    _transcript(db, project.id)

    result = await pipeline.run_segment(ctx, project.id)
    assert "2 clips" in result

    db.expire_all()
    clips = db.query(Clip).filter_by(project_id=project.id).order_by(Clip.score.desc()).all()
    assert [c.score for c in clips] == [92, 74]
    assert all(c.status == ClipStatus.queued for c in clips)
    assert all(c.user_id == auth_user.id for c in clips)

    captions = db.query(ClipCaption).all()
    assert len(captions) == 2

    job = db.query(ProcessingJob).filter_by(project_id=project.id, job_type=JobType.segment).one()
    assert job.status == JobStatus.completed
    assert ctx["redis"].enqueue_job.await_count == 2


async def test_run_render_marks_clip_ready_and_completes_project(ctx, db, auth_user):
    project = _url_project(db, user_id=auth_user.id)
    project.storage_key = "projects/1/source.mp4"
    db.commit()
    clip = Clip(
        project_id=project.id,
        user_id=auth_user.id,
        title="c",
        start_seconds=0.0,
        end_seconds=30.0,
        duration_seconds=30.0,
        status=ClipStatus.queued,
        score=80,
    )
    db.add(clip)
    db.commit()
    db.refresh(clip)

    out_key = await pipeline.run_render(ctx, clip.id)
    assert out_key.endswith(".mp4")

    db.expire_all()
    reloaded = db.get(Clip, clip.id)
    assert reloaded.status == ClipStatus.ready
    assert reloaded.storage_key == out_key
    assert db.get(Project, project.id).status == ProjectStatus.completed


async def test_full_chain_end_to_end(ctx, db, auth_user):
    project = _url_project(db, user_id=auth_user.id)

    await pipeline.run_download(ctx, project.id)
    await pipeline.run_transcribe(ctx, project.id)
    await pipeline.run_segment(ctx, project.id)

    db.expire_all()
    clip_ids = [c.id for c in db.query(Clip).filter_by(project_id=project.id).all()]
    assert len(clip_ids) == 2
    for clip_id in clip_ids:
        await pipeline.run_render(ctx, clip_id)

    db.expire_all()
    assert db.get(Project, project.id).status == ProjectStatus.completed
    assert all(c.status == ClipStatus.ready for c in db.query(Clip).all())
    render_job = (
        db.query(ProcessingJob)
        .filter_by(project_id=project.id, job_type=JobType.render)
        .one()
    )
    assert render_job.status == JobStatus.completed


async def test_segment_rerun_is_idempotent(ctx, db, auth_user):
    project = _url_project(db, user_id=auth_user.id)
    project.storage_key = "projects/1/source.mp4"
    db.commit()
    _transcript(db, project.id)

    await pipeline.run_segment(ctx, project.id)
    await pipeline.run_segment(ctx, project.id)

    db.expire_all()
    assert db.query(Clip).filter_by(project_id=project.id).count() == 2
    assert db.query(ClipCaption).count() == 2
    # still exactly one segment job row, back to completed
    jobs = db.query(ProcessingJob).filter_by(project_id=project.id, job_type=JobType.segment).all()
    assert len(jobs) == 1
    assert jobs[0].status == JobStatus.completed


async def test_transcribe_rerun_keeps_single_transcript(ctx, db, auth_user):
    project = _url_project(db, user_id=auth_user.id)
    project.storage_key = "projects/1/source.mp4"
    db.commit()

    await pipeline.run_transcribe(ctx, project.id)
    await pipeline.run_transcribe(ctx, project.id)

    db.expire_all()
    assert db.query(Transcript).filter_by(project_id=project.id).count() == 1


async def test_run_download_missing_project_is_noop(ctx, db):
    assert await pipeline.run_download(ctx, 999999) == "missing"


async def test_run_download_failure_marks_job_and_project_failed(ctx, db, auth_user, monkeypatch):
    project = _url_project(db, user_id=auth_user.id)

    def _boom(url, dest):
        raise RuntimeError("network down")

    monkeypatch.setattr("app.workers.pipeline._download_url", _boom)

    with pytest.raises(RuntimeError):
        await pipeline.run_download(ctx, project.id)

    db.expire_all()
    assert db.get(Project, project.id).status == ProjectStatus.failed
    job = db.query(ProcessingJob).filter_by(
        project_id=project.id, job_type=JobType.download
    ).one()
    assert job.status == JobStatus.failed
    assert "network down" in job.error_message


async def test_run_download_youtube_url_uses_ytdlp(ctx, db, auth_user, monkeypatch):
    project = _url_project(db, user_id=auth_user.id)
    project.source_url = "https://www.youtube.com/watch?v=abc123"
    db.commit()

    calls: dict[str, str] = {}

    def _fake_ytdlp(url, dest, workdir):
        calls["url"] = url
        with open(dest, "wb") as fh:
            fh.write(b"\x00\x00\x00\x18ftypmp42 fake video bytes")
        return "Real Video Title"

    monkeypatch.setattr("app.workers.pipeline._download_with_ytdlp", _fake_ytdlp)

    def _boom_http(url, dest):
        raise AssertionError("a YouTube page URL must not be fetched over plain HTTP")

    monkeypatch.setattr("app.workers.pipeline._download_url", _boom_http)

    await pipeline.run_download(ctx, project.id)

    assert calls["url"] == "https://www.youtube.com/watch?v=abc123"
    db.expire_all()
    reloaded = db.get(Project, project.id)
    assert reloaded.storage_key is not None
    # "P" is a placeholder title -> replaced by the yt-dlp title.
    assert reloaded.title == "Real Video Title"
    ctx["redis"].enqueue_job.assert_awaited_with("run_transcribe", project.id)


async def test_run_download_rejects_unsupported_page_url(ctx, db, auth_user):
    project = _url_project(db, user_id=auth_user.id)
    project.source_url = "https://some-random-blog.example/post"
    db.commit()

    with pytest.raises(ValueError, match="Unsupported URL"):
        await pipeline.run_download(ctx, project.id)

    db.expire_all()
    assert db.get(Project, project.id).status == ProjectStatus.failed


async def test_run_segment_without_transcript_raises(ctx, db, auth_user):
    project = _url_project(db, user_id=auth_user.id)
    project.storage_key = "projects/1/source.mp4"
    db.commit()
    with pytest.raises(RuntimeError):
        await pipeline.run_segment(ctx, project.id)


async def test_run_download_non_url_project_skips_to_transcribe(ctx, db, auth_user):
    project = Project(
        user_id=auth_user.id,
        title="upload",
        source_type=SourceType.upload,
        status=ProjectStatus.pending,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    result = await pipeline.run_download(ctx, project.id)
    assert result == "skipped"
    ctx["redis"].enqueue_job.assert_awaited_with("run_transcribe", project.id)


async def test_run_segment_no_clips_completes_project(ctx, db, auth_user, monkeypatch):
    project = _url_project(db, user_id=auth_user.id)
    project.storage_key = "projects/1/source.mp4"
    db.commit()
    _transcript(db, project.id)

    monkeypatch.setattr("app.services.segmentation.detect_segments", lambda t: [])

    await pipeline.run_segment(ctx, project.id)

    db.expire_all()
    assert db.get(Project, project.id).status == ProjectStatus.completed
