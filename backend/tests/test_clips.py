"""Clips module."""

from __future__ import annotations

from app.models.clip import Clip, ClipStatus
from app.models.clip_caption import ClipCaption
from app.models.project import Project, ProjectStatus, SourceType


def _project(db, user_id, **kw):
    project = Project(
        user_id=user_id,
        title=kw.get("title", "P"),
        source_type=SourceType.url,
        source_url="https://example.com/v.mp4",
        storage_key="projects/x/source.mp4",
        status=ProjectStatus.completed,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def _clip(db, project, user_id, **kw):
    clip = Clip(
        project_id=project.id,
        user_id=user_id,
        title=kw.get("title", "Clip"),
        start_seconds=kw.get("start_seconds", 0.0),
        end_seconds=kw.get("end_seconds", 30.0),
        duration_seconds=kw.get("duration_seconds", 30.0),
        status=kw.get("status", ClipStatus.queued),
        score=kw.get("score", 50),
        score_reason="because",
        storage_key=kw.get("storage_key"),
    )
    db.add(clip)
    db.commit()
    db.refresh(clip)
    return clip


def test_list_clips_for_project_ordered_by_score(auth_client, auth_user, db):
    project = _project(db, auth_user.id)
    _clip(db, project, auth_user.id, title="low", score=10)
    _clip(db, project, auth_user.id, title="high", score=95)
    _clip(db, project, auth_user.id, title="mid", score=55)

    resp = auth_client.get(f"/api/v1/projects/{project.id}/clips")
    assert resp.status_code == 200
    titles = [c["title"] for c in resp.json()["items"]]
    assert titles == ["high", "mid", "low"]


def test_list_clips_rejects_non_owner(client, make_user, db):
    user_a, token_a = make_user("a@test.com")
    user_b, token_b = make_user("b@test.com")
    project = _project(db, user_a.id)
    _clip(db, project, user_a.id)

    client.headers.update({"Authorization": f"Bearer {token_b}"})
    assert client.get(f"/api/v1/projects/{project.id}/clips").status_code == 404


def test_get_clip_cross_user_404(client, make_user, db):
    user_a, token_a = make_user("a@test.com")
    user_b, token_b = make_user("b@test.com")
    project = _project(db, user_a.id)
    clip = _clip(db, project, user_a.id)

    client.headers.update({"Authorization": f"Bearer {token_b}"})
    assert client.get(f"/api/v1/clips/{clip.id}").status_code == 404


def test_get_clip_detail(auth_client, auth_user, db):
    project = _project(db, auth_user.id)
    clip = _clip(db, project, auth_user.id, status=ClipStatus.ready, storage_key="k.mp4")
    db.add(ClipCaption(clip_id=clip.id, segments=[{"start": 0, "end": 2, "text": "hi"}], edited=False))
    db.commit()

    resp = auth_client.get(f"/api/v1/clips/{clip.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["download_available"] is True
    assert body["caption_segments"][0]["text"] == "hi"


def test_update_trim_requeues_and_enqueues_render(auth_client, auth_user, db, fake_enqueue):
    project = _project(db, auth_user.id)
    clip = _clip(db, project, auth_user.id, status=ClipStatus.ready, storage_key="k.mp4")

    resp = auth_client.put(
        f"/api/v1/clips/{clip.id}",
        json={"start_seconds": 5.0, "end_seconds": 40.0},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"
    fake_enqueue.assert_awaited_with("run_render", clip.id)

    db.expire_all()
    assert db.get(Clip, clip.id).status == ClipStatus.queued


def test_update_title_only_does_not_requeue(auth_client, auth_user, db, fake_enqueue):
    project = _project(db, auth_user.id)
    clip = _clip(db, project, auth_user.id, status=ClipStatus.ready, storage_key="k.mp4")

    resp = auth_client.put(f"/api/v1/clips/{clip.id}", json={"title": "Renamed"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"
    fake_enqueue.assert_not_awaited()


def test_update_invalid_trim_conflicts(auth_client, auth_user, db):
    project = _project(db, auth_user.id)
    clip = _clip(db, project, auth_user.id)
    resp = auth_client.put(
        f"/api/v1/clips/{clip.id}", json={"start_seconds": 20.0, "end_seconds": 10.0}
    )
    assert resp.status_code == 422  # schema-level validator


def test_rerender_enqueues(auth_client, auth_user, db, fake_enqueue):
    project = _project(db, auth_user.id)
    clip = _clip(db, project, auth_user.id, status=ClipStatus.ready, storage_key="k.mp4")

    resp = auth_client.post(f"/api/v1/clips/{clip.id}/rerender")
    assert resp.status_code == 202
    assert resp.json()["status"] == "queued"
    fake_enqueue.assert_awaited_with("run_render", clip.id)


def test_download_409_when_not_ready(auth_client, auth_user, db):
    project = _project(db, auth_user.id)
    clip = _clip(db, project, auth_user.id, status=ClipStatus.queued)
    resp = auth_client.get(f"/api/v1/clips/{clip.id}/download")
    assert resp.status_code == 409


def test_download_200_signed_url_when_ready(auth_client, auth_user, db):
    project = _project(db, auth_user.id)
    clip = _clip(
        db, project, auth_user.id, status=ClipStatus.ready, storage_key="projects/x/clips/1.mp4"
    )
    resp = auth_client.get(f"/api/v1/clips/{clip.id}/download")
    assert resp.status_code == 200
    body = resp.json()
    assert body["url"].startswith("https://signed.test/get_object/")
    assert "expires_at" in body


def test_delete_clip(auth_client, auth_user, db):
    project = _project(db, auth_user.id)
    clip = _clip(db, project, auth_user.id, status=ClipStatus.ready, storage_key="k.mp4")
    resp = auth_client.delete(f"/api/v1/clips/{clip.id}")
    assert resp.status_code == 204
    assert db.get(Clip, clip.id) is None
