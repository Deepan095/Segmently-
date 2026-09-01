"""Projects / Uploads module."""

from __future__ import annotations

import pytest

from app.models.clip import Clip, ClipStatus
from app.models.processing_job import JobType, ProcessingJob
from app.models.project import Project, ProjectStatus, SourceType
from app.models.transcript import Transcript


def _create_url_project(client, url="https://example.com/video.mp4", title="My clip"):
    return client.post("/api/v1/projects", json={"url": url, "title": title})


def test_create_from_url_enqueues_download(auth_client, fake_enqueue):
    resp = _create_url_project(auth_client)
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["source_type"] == "url"
    assert body["status"] == "pending"
    fake_enqueue.assert_awaited_with("run_download", body["id"])


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/video.mp4",
        "http://169.254.169.254/latest/meta-data",
        "http://192.168.1.10/x.mp4",
        "ftp://example.com/x.mp4",
    ],
)
def test_create_from_url_rejects_unsafe_url(auth_client, url):
    resp = auth_client.post("/api/v1/projects", json={"url": url})
    assert resp.status_code == 422


def test_list_projects_is_per_user(client, make_user, fake_enqueue):
    user_a, token_a = make_user("a@test.com")
    user_b, token_b = make_user("b@test.com")

    client.headers.update({"Authorization": f"Bearer {token_a}"})
    _create_url_project(client)

    client.headers.update({"Authorization": f"Bearer {token_b}"})
    resp = client.get("/api/v1/projects")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0

    client.headers.update({"Authorization": f"Bearer {token_a}"})
    assert client.get("/api/v1/projects").json()["total"] == 1


def test_get_other_users_project_returns_404(client, make_user, db, fake_enqueue):
    user_a, token_a = make_user("a@test.com")
    user_b, token_b = make_user("b@test.com")

    client.headers.update({"Authorization": f"Bearer {token_a}"})
    pid = _create_url_project(client).json()["id"]

    client.headers.update({"Authorization": f"Bearer {token_b}"})
    assert client.get(f"/api/v1/projects/{pid}").status_code == 404
    assert client.delete(f"/api/v1/projects/{pid}").status_code == 404
    assert client.post(f"/api/v1/projects/{pid}/reprocess").status_code == 404


def test_delete_cascades_children(auth_client, auth_user, db):
    project = Project(
        user_id=auth_user.id,
        title="P",
        source_type=SourceType.url,
        source_url="https://example.com/v.mp4",
        status=ProjectStatus.completed,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    db.add(Transcript(project_id=project.id, full_text="hi", segments=[]))
    db.add(ProcessingJob(project_id=project.id, job_type=JobType.download))
    db.add(
        Clip(
            project_id=project.id,
            user_id=auth_user.id,
            title="c",
            start_seconds=0,
            end_seconds=10,
            duration_seconds=10,
            status=ClipStatus.ready,
        )
    )
    db.commit()

    resp = auth_client.delete(f"/api/v1/projects/{project.id}")
    assert resp.status_code == 200

    assert db.query(Project).count() == 0
    assert db.query(Transcript).count() == 0
    assert db.query(ProcessingJob).count() == 0
    assert db.query(Clip).count() == 0


def test_reprocess_enqueues(auth_client, auth_user, db, fake_enqueue):
    pid = _create_url_project(auth_client).json()["id"]
    fake_enqueue.reset_mock()

    resp = auth_client.post(f"/api/v1/projects/{pid}/reprocess")
    assert resp.status_code == 202
    assert resp.json()["status"] == "pending"
    fake_enqueue.assert_awaited()
    assert fake_enqueue.await_args.args[0] in {"run_download", "run_transcribe"}


def test_transcript_404_until_present_then_returned(auth_client, auth_user, db):
    project = Project(
        user_id=auth_user.id,
        title="P",
        source_type=SourceType.url,
        status=ProjectStatus.transcribing,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    assert auth_client.get(f"/api/v1/projects/{project.id}/transcript").status_code == 404

    db.add(
        Transcript(
            project_id=project.id,
            language="en",
            full_text="the transcript",
            segments=[{"start": 0.0, "end": 1.0, "text": "the transcript"}],
        )
    )
    db.commit()

    resp = auth_client.get(f"/api/v1/projects/{project.id}/transcript")
    assert resp.status_code == 200
    assert resp.json()["full_text"] == "the transcript"


def test_multipart_upload_creates_project_and_enqueues_transcribe(auth_client, fake_enqueue):
    resp = auth_client.post(
        "/api/v1/projects/upload",
        files={"file": ("clip.mp4", b"binary-bytes", "video/mp4")},
        data={"title": "Uploaded"},
    )
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["source_type"] == "upload"
    fake_enqueue.assert_awaited_with("run_transcribe", body["id"])


def test_multipart_upload_rejects_bad_content_type(auth_client):
    resp = auth_client.post(
        "/api/v1/projects/upload",
        files={"file": ("bad.txt", b"nope", "text/plain")},
    )
    assert resp.status_code == 422


def test_presigned_upload_init_and_complete(auth_client, auth_user, db, fake_enqueue):
    init = auth_client.post(
        "/api/v1/projects/upload/init",
        json={
            "filename": "big.mp4",
            "content_type": "video/mp4",
            "file_size_bytes": 12345,
            "title": "Big",
        },
    )
    assert init.status_code == 201, init.text
    body = init.json()
    assert body["upload_url"].startswith("https://signed.test/put_object/")
    assert body["storage_key"].startswith("projects/")
    pid = body["project_id"]

    # object must exist in storage for the complete call to pass
    from app.services import storage

    storage.put_object(body["storage_key"], b"video-bytes")

    done = auth_client.post(f"/api/v1/projects/{pid}/upload/complete")
    assert done.status_code == 202
    fake_enqueue.assert_awaited_with("run_transcribe", pid)


def test_presigned_upload_init_rejects_oversize(auth_client):
    resp = auth_client.post(
        "/api/v1/projects/upload/init",
        json={
            "filename": "huge.mp4",
            "content_type": "video/mp4",
            "file_size_bytes": 999_999_999_999_999,
        },
    )
    assert resp.status_code == 422


def test_detail_includes_jobs_and_clip_count(auth_client, auth_user, db):
    project = Project(
        user_id=auth_user.id,
        title="P",
        source_type=SourceType.url,
        status=ProjectStatus.rendering,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    db.add(ProcessingJob(project_id=project.id, job_type=JobType.transcribe))
    db.add(
        Clip(
            project_id=project.id,
            user_id=auth_user.id,
            title="c",
            start_seconds=0,
            end_seconds=5,
            duration_seconds=5,
        )
    )
    db.commit()

    resp = auth_client.get(f"/api/v1/projects/{project.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["clips_count"] == 1
    assert len(body["jobs"]) == 1
    assert body["has_transcript"] is False
