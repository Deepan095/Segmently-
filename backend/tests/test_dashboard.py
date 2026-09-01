"""Analytics dashboard module."""

from __future__ import annotations

from app.models.clip import Clip, ClipStatus
from app.models.project import Project, ProjectStatus, SourceType


def _project(db, user_id, duration, status=ProjectStatus.completed):
    p = Project(
        user_id=user_id,
        title="P",
        source_type=SourceType.url,
        status=status,
        duration_seconds=duration,
        file_size_bytes=1000,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _clip(db, project_id, user_id, score, status=ClipStatus.ready):
    c = Clip(
        project_id=project_id,
        user_id=user_id,
        title=f"clip-{score}",
        start_seconds=0,
        end_seconds=30,
        duration_seconds=30,
        score=score,
        status=status,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_summary_totals(auth_client, auth_user, db):
    p1 = _project(db, auth_user.id, 600)
    p2 = _project(db, auth_user.id, 1200, status=ProjectStatus.failed)
    _clip(db, p1.id, auth_user.id, 80)
    _clip(db, p1.id, auth_user.id, 40, status=ClipStatus.queued)

    resp = auth_client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["minutes_uploaded"] == 30.0
    assert body["projects_total"] == 2
    assert body["projects_completed"] == 1
    assert body["clips_generated"] == 2
    assert body["clips_downloaded"] == 1  # proxy: clips in 'ready'


def test_summary_is_per_user(client, make_user, db):
    user_a, token_a = make_user("a@test.com")
    user_b, token_b = make_user("b@test.com")
    p = _project(db, user_a.id, 600)
    _clip(db, p.id, user_a.id, 90)

    client.headers.update({"Authorization": f"Bearer {token_b}"})
    body = client.get("/api/v1/dashboard/summary").json()
    assert body["projects_total"] == 0
    assert body["clips_generated"] == 0


def test_usage_zero_fills_one_point_per_day(auth_client, auth_user, db):
    p = _project(db, auth_user.id, 300)
    _clip(db, p.id, auth_user.id, 70)

    resp = auth_client.get("/api/v1/dashboard/usage?range=30d")
    assert resp.status_code == 200
    points = resp.json()["points"]
    assert len(points) == 30
    dates = [pt["date"] for pt in points]
    assert dates == sorted(dates)
    assert len(set(dates)) == 30
    # today's bucket carries the seeded activity
    assert sum(pt["clips_generated"] for pt in points) == 1
    assert round(sum(pt["minutes_processed"] for pt in points), 2) == 5.0


def test_usage_range_7d(auth_client, auth_user, db):
    resp = auth_client.get("/api/v1/dashboard/usage?range=7d")
    assert resp.status_code == 200
    assert len(resp.json()["points"]) == 7


def test_top_clips_ordered_by_score_desc(auth_client, auth_user, db):
    p = _project(db, auth_user.id, 600)
    _clip(db, p.id, auth_user.id, 10)
    _clip(db, p.id, auth_user.id, 99)
    _clip(db, p.id, auth_user.id, 55)

    resp = auth_client.get("/api/v1/dashboard/top-clips?limit=2")
    assert resp.status_code == 200
    scores = [c["score"] for c in resp.json()]
    assert scores == [99, 55]


def test_top_clips_per_user(client, make_user, db):
    user_a, token_a = make_user("a@test.com")
    user_b, token_b = make_user("b@test.com")
    p = _project(db, user_a.id, 600)
    _clip(db, p.id, user_a.id, 88)

    client.headers.update({"Authorization": f"Bearer {token_b}"})
    assert client.get("/api/v1/dashboard/top-clips").json() == []


def test_dashboard_requires_auth(client):
    assert client.get("/api/v1/dashboard/summary").status_code == 401
