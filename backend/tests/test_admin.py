"""Admin panel module."""

from __future__ import annotations

import pytest

from app.models.processing_job import JobStatus, JobType, ProcessingJob
from app.models.project import Project, ProjectStatus, SourceType

ADMIN_ROUTES = [
    ("get", "/api/v1/admin/users"),
    ("get", "/api/v1/admin/stats"),
    ("get", "/api/v1/admin/jobs"),
    ("put", "/api/v1/admin/users/1"),
    ("post", "/api/v1/admin/jobs/1/retry"),
]


@pytest.mark.parametrize("method,path", ADMIN_ROUTES)
def test_non_admin_forbidden_on_every_route(auth_client, method, path):
    resp = auth_client.request(method.upper(), path, json={})
    assert resp.status_code == 403


@pytest.mark.parametrize("method,path", ADMIN_ROUTES)
def test_unauthenticated_rejected_on_every_route(client, method, path):
    resp = client.request(method.upper(), path, json={})
    assert resp.status_code == 401


def test_admin_lists_users_with_counts(admin_client, admin_user, db, make_user):
    make_user("regular@test.com")
    resp = admin_client.get("/api/v1/admin/users")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    emails = {u["email"] for u in body["items"]}
    assert emails == {"admin@test.com", "regular@test.com"}
    assert all("projects_count" in u and "clips_count" in u for u in body["items"])


def test_admin_search_users(admin_client, admin_user, make_user):
    make_user("alice@test.com")
    make_user("bob@test.com")
    resp = admin_client.get("/api/v1/admin/users", params={"q": "alice"})
    assert [u["email"] for u in resp.json()["items"]] == ["alice@test.com"]


def test_admin_updates_user_flags(admin_client, db, make_user):
    user, _ = make_user("target@test.com")
    resp = admin_client.put(
        f"/api/v1/admin/users/{user.id}",
        json={"is_active": False, "is_verified": True, "is_admin": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_active"] is False
    assert body["is_verified"] is True
    assert body["is_admin"] is True


def test_admin_cannot_self_demote(admin_client, admin_user):
    resp = admin_client.put(
        f"/api/v1/admin/users/{admin_user.id}", json={"is_admin": False}
    )
    assert resp.status_code == 409


def test_admin_update_missing_user_404(admin_client):
    assert admin_client.put("/api/v1/admin/users/99999", json={"is_active": False}).status_code == 404


def test_platform_stats_shape(admin_client, admin_user, db, make_user):
    user, _ = make_user("u@test.com")
    p = Project(
        user_id=user.id,
        title="P",
        source_type=SourceType.upload,
        status=ProjectStatus.failed,
        file_size_bytes=2048,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    db.add(ProcessingJob(project_id=p.id, job_type=JobType.render, status=JobStatus.failed))
    db.commit()

    resp = admin_client.get("/api/v1/admin/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {
        "users_total",
        "users_active",
        "projects_total",
        "clips_total",
        "storage_bytes_estimate",
        "jobs_failed",
    }
    assert body["users_total"] == 2
    assert body["projects_total"] == 1
    assert body["storage_bytes_estimate"] == 2048
    assert body["jobs_failed"] == 1


def test_admin_lists_jobs_with_status_filter(admin_client, db, make_user):
    user, _ = make_user("j@test.com")
    p = Project(user_id=user.id, title="P", source_type=SourceType.url, status=ProjectStatus.pending)
    db.add(p)
    db.commit()
    db.refresh(p)
    db.add(ProcessingJob(project_id=p.id, job_type=JobType.download, status=JobStatus.completed))
    db.add(ProcessingJob(project_id=p.id, job_type=JobType.transcribe, status=JobStatus.failed))
    db.commit()

    all_jobs = admin_client.get("/api/v1/admin/jobs").json()
    assert all_jobs["total"] == 2

    failed = admin_client.get("/api/v1/admin/jobs", params={"status": "failed"}).json()
    assert failed["total"] == 1
    assert failed["items"][0]["status"] == "failed"


def test_retry_failed_job_requeues_and_enqueues(admin_client, db, make_user, fake_enqueue):
    user, _ = make_user("r@test.com")
    p = Project(user_id=user.id, title="P", source_type=SourceType.url, status=ProjectStatus.failed)
    db.add(p)
    db.commit()
    db.refresh(p)
    job = ProcessingJob(
        project_id=p.id,
        job_type=JobType.segment,
        status=JobStatus.failed,
        progress_pct=40,
        error_message="boom",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    resp = admin_client.post(f"/api/v1/admin/jobs/{job.id}/retry")
    assert resp.status_code == 202
    assert resp.json()["status"] == "queued"
    fake_enqueue.assert_awaited()

    db.expire_all()
    reloaded = db.get(ProcessingJob, job.id)
    assert reloaded.status == JobStatus.queued
    assert reloaded.progress_pct == 0
    assert reloaded.error_message is None


def test_retry_non_failed_job_conflicts(admin_client, db, make_user):
    user, _ = make_user("r2@test.com")
    p = Project(user_id=user.id, title="P", source_type=SourceType.url, status=ProjectStatus.pending)
    db.add(p)
    db.commit()
    db.refresh(p)
    job = ProcessingJob(project_id=p.id, job_type=JobType.download, status=JobStatus.running)
    db.add(job)
    db.commit()
    db.refresh(job)

    assert admin_client.post(f"/api/v1/admin/jobs/{job.id}/retry").status_code == 409


def test_retry_missing_job_404(admin_client):
    assert admin_client.post("/api/v1/admin/jobs/4242/retry").status_code == 404
