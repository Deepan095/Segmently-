"""Auth module: register / login / me / refresh / logout."""

from __future__ import annotations

from app.models.refresh_token import RefreshToken


def test_register_happy(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "new@test.com", "password": "password123", "full_name": "New"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == "new@test.com"
    assert body["is_admin"] is False
    assert "hashed_password" not in body


def test_register_duplicate_email(client):
    payload = {"email": "dup@test.com", "password": "password123"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409
    assert resp.json()["code"] == "CONFLICT"


def test_register_weak_password(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "weak@test.com", "password": "short"},
    )
    assert resp.status_code == 422


def test_login_happy(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "login@test.com", "password": "password123"},
    )
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "login@test.com", "password": "password123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["token_type"] == "bearer"


def test_login_bad_credentials(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "bad@test.com", "password": "password123"},
    )
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "bad@test.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "ghost@test.com", "password": "password123"},
    )
    assert resp.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_with_token(auth_client):
    resp = auth_client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "user@test.com"


def test_me_rejects_garbage_token(client):
    resp = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert resp.status_code == 401


def test_update_profile(auth_client):
    resp = auth_client.put("/api/v1/auth/me", json={"full_name": "Renamed"})
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Renamed"


def test_refresh_rotates_and_revokes_old(client, db):
    client.post(
        "/api/v1/auth/register",
        json={"email": "rot@test.com", "password": "password123"},
    )
    tokens = client.post(
        "/api/v1/auth/login",
        data={"username": "rot@test.com", "password": "password123"},
    ).json()
    old_refresh = tokens["refresh_token"]

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 200
    new_tokens = resp.json()
    assert new_tokens["refresh_token"] != old_refresh

    # old row is now revoked
    old_row = db.query(RefreshToken).filter(RefreshToken.token == old_refresh).one()
    assert old_row.revoked is True

    # reusing the old refresh token now fails
    reuse = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse.status_code == 401


def test_logout_revokes_refresh_token(client, db):
    client.post(
        "/api/v1/auth/register",
        json={"email": "out@test.com", "password": "password123"},
    )
    tokens = client.post(
        "/api/v1/auth/login",
        data={"username": "out@test.com", "password": "password123"},
    ).json()
    refresh = tokens["refresh_token"]

    resp = client.post("/api/v1/auth/logout", json={"refresh_token": refresh})
    assert resp.status_code == 204

    row = db.query(RefreshToken).filter(RefreshToken.token == refresh).one()
    assert row.revoked is True

    # a revoked token cannot be rotated
    assert (
        client.post("/api/v1/auth/refresh", json={"refresh_token": refresh}).status_code
        == 401
    )


def test_health():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        assert c.get("/health").json()["status"] == "healthy"
