"""Google OAuth helpers, the OAuth endpoints, and admin seeding."""

from __future__ import annotations

import pytest

from app.auth import oauth
from app.auth.seed import seed_admin
from app.models.user import User
from app.services import auth_service


# --------------------------------------------------------------------------- #
# oauth.py helpers
# --------------------------------------------------------------------------- #
def test_oauth_state_roundtrip():
    state = oauth.create_oauth_state()
    assert oauth.verify_oauth_state(state) is True
    assert oauth.verify_oauth_state("garbage") is False


def test_verify_rejects_non_state_token():
    from app.auth.jwt import create_access_token

    assert oauth.verify_oauth_state(create_access_token({"sub": "1"})) is False


def test_build_authorization_url_contains_params():
    url = oauth.build_authorization_url("st-123")
    assert url.startswith(oauth.GOOGLE_AUTH_URL)
    assert "state=st-123" in url
    assert "response_type=code" in url


class _FakeResp:
    def __init__(self, status, data):
        self.status_code = status
        self._data = data
        self.text = str(data)

    def json(self):
        return self._data


class _FakeAsyncClient:
    token_data = {"access_token": "g-access"}
    userinfo = {"sub": "google-sub-1", "email": "guser@example.com", "name": "G User"}

    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, data=None):
        return _FakeResp(200, self.token_data)

    async def get(self, url, headers=None):
        return _FakeResp(200, self.userinfo)


@pytest.fixture
def fake_google_http(monkeypatch):
    monkeypatch.setattr("app.auth.oauth.httpx.AsyncClient", _FakeAsyncClient)


async def test_exchange_and_fetch_userinfo(fake_google_http):
    tok = await oauth.exchange_code_for_token("code-abc")
    assert tok["access_token"] == "g-access"
    info = await oauth.fetch_userinfo("g-access")
    assert info["email"] == "guser@example.com"


async def test_exchange_failure_raises(monkeypatch):
    class _Bad(_FakeAsyncClient):
        async def post(self, url, data=None):
            return _FakeResp(400, {"error": "invalid_grant"})

    monkeypatch.setattr("app.auth.oauth.httpx.AsyncClient", _Bad)
    with pytest.raises(oauth.OAuthError):
        await oauth.exchange_code_for_token("bad")


# --------------------------------------------------------------------------- #
# /auth/google/* endpoints
# --------------------------------------------------------------------------- #
def test_google_login_redirects(client, monkeypatch):
    monkeypatch.setattr("app.routers.auth.settings.GOOGLE_CLIENT_ID", "cid-1")
    resp = client.get("/api/v1/auth/google/login", follow_redirects=False)
    assert resp.status_code == 302
    assert "accounts.google.com" in resp.headers["location"]


def test_google_login_unconfigured(client, monkeypatch):
    monkeypatch.setattr("app.routers.auth.settings.GOOGLE_CLIENT_ID", "")
    assert client.get("/api/v1/auth/google/login", follow_redirects=False).status_code == 422


def test_google_callback_provisions_user_and_redirects(client, db, fake_google_http):
    state = oauth.create_oauth_state()
    resp = client.get(
        "/api/v1/auth/google/callback",
        params={"code": "code-abc", "state": state},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    loc = resp.headers["location"]
    assert "access_token=" in loc and "refresh_token=" in loc

    user = db.query(User).filter(User.email == "guser@example.com").one()
    assert user.oauth_provider == "google"
    assert user.is_verified is True


def test_google_callback_rejects_bad_state(client):
    resp = client.get(
        "/api/v1/auth/google/callback",
        params={"code": "x", "state": "not-valid"},
        follow_redirects=False,
    )
    assert resp.status_code == 401


def test_google_callback_missing_code(client):
    resp = client.get(
        "/api/v1/auth/google/callback", params={"state": "s"}, follow_redirects=False
    )
    assert resp.status_code == 422


def test_google_callback_upstream_error(client):
    resp = client.get(
        "/api/v1/auth/google/callback",
        params={"error": "access_denied"},
        follow_redirects=False,
    )
    assert resp.status_code == 401


# --------------------------------------------------------------------------- #
# auth_service.get_or_create_google_user
# --------------------------------------------------------------------------- #
def test_google_user_links_to_existing_email_account(db):
    existing = auth_service.register_user(db, "linkme@example.com", "password123")
    assert existing.oauth_provider is None

    user, tokens = auth_service.get_or_create_google_user(
        db, sub="sub-xyz", email="linkme@example.com", full_name="Linked"
    )
    assert user.id == existing.id
    assert user.oauth_provider == "google"
    assert tokens.access_token

    # Second call finds the same linked user via oauth_sub.
    again, _ = auth_service.get_or_create_google_user(
        db, sub="sub-xyz", email="linkme@example.com", full_name="Linked"
    )
    assert again.id == existing.id


# --------------------------------------------------------------------------- #
# seed.py
# --------------------------------------------------------------------------- #
def test_seed_admin_creates_then_idempotent(db):
    a1 = seed_admin(db)
    assert a1.is_admin and a1.is_active and a1.is_verified
    a2 = seed_admin(db)
    assert a2.id == a1.id
    assert db.query(User).count() == 1


def test_seed_admin_repairs_flags(db):
    from app.auth.jwt import hash_password
    from app.config import settings

    weak = User(
        email=settings.ADMIN_EMAIL.lower(),
        hashed_password=hash_password("x"),
        is_admin=False,
        is_active=False,
        is_verified=False,
    )
    db.add(weak)
    db.commit()

    repaired = seed_admin(db)
    assert repaired.is_admin and repaired.is_active and repaired.is_verified
