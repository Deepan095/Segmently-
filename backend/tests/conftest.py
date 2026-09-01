"""Shared pytest fixtures for the Segmently backend test suite.

* In-memory SQLite (StaticPool) stands in for PostgreSQL.
* ``app.database.engine`` / ``SessionLocal`` are re-pointed at that engine so the
  arq worker pipeline (which opens its own sessions) and the FastAPI request
  handlers share one database.
* Every external dependency - the arq queue, S3 storage, Whisper, Anthropic and
  FFmpeg - is monkeypatched to a deterministic in-process fake by the autouse
  ``_external_fakes`` fixture.
"""

from __future__ import annotations

import os

# The test suite runs with the shipped default SECRET_KEY etc.; mark the
# environment as DEBUG before anything imports app.config so its
# production-secrets guard stays quiet.
os.environ.setdefault("DEBUG", "true")

from collections.abc import Iterator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.database as database_module

# --- Re-point the database at an in-memory SQLite engine BEFORE app import ----
TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)
TestSessionLocal = sessionmaker(
    bind=TEST_ENGINE, autocommit=False, autoflush=False, future=True
)


@event.listens_for(TEST_ENGINE, "connect")
def _enable_sqlite_fk(dbapi_connection, _record):
    """Enforce FK / ON DELETE CASCADE like PostgreSQL does."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

database_module.engine = TEST_ENGINE
database_module.SessionLocal = TestSessionLocal

from app.database import Base  # noqa: E402
import app.models  # noqa: E402,F401  (populate Base.metadata)
from app.dependencies import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.auth.jwt import hash_password  # noqa: E402
from app.models.user import User  # noqa: E402


# --------------------------------------------------------------------------- #
# Database
# --------------------------------------------------------------------------- #
@pytest.fixture
def db() -> Iterator[Session]:
    """A fresh schema + session per test."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    """TestClient whose ``get_db`` dependency yields the test session."""

    def _override_get_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# --------------------------------------------------------------------------- #
# External-dependency fakes (autouse)
# --------------------------------------------------------------------------- #
@pytest.fixture
def fake_enqueue() -> AsyncMock:
    """The single AsyncMock used everywhere ``enqueue`` is called."""
    return AsyncMock(return_value="job-id-1")


def _fake_transcribe(path: str) -> dict:
    return {
        "language": "en",
        "full_text": "hello world this is the transcript body",
        "segments": [
            {"start": 0.0, "end": 60.0, "text": "hello world"},
            {"start": 60.0, "end": 120.0, "text": "this is the transcript body"},
        ],
    }


def _fake_detect_segments(transcript: dict) -> list[dict]:
    return [
        {
            "start": 0.0,
            "end": 55.0,
            "title": "Strong opening moment",
            "score": 92,
            "score_reason": "clear hook",
        },
        {
            "start": 60.0,
            "end": 118.0,
            "title": "Payoff moment",
            "score": 74,
            "score_reason": "emotional beat",
        },
    ]


def _fake_render_clip(source_key, start, end, captions, style, *, project_id, clip_id):
    return f"projects/{project_id}/clips/{clip_id}.mp4"


def _fake_download_file(key: str, local_path: str) -> str:
    with open(local_path, "wb") as fh:
        fh.write(b"fake-media-bytes")
    return local_path


class FakeS3Client:
    """Minimal in-memory stand-in for a boto3 S3 client.

    Lets the *real* ``app.services.storage`` code run under test (only
    ``get_client`` is patched) while never touching the network.
    """

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_object(self, Bucket, Key, Body, **extra):  # noqa: N803
        self.objects[Key] = Body if isinstance(Body, bytes) else b"stream"
        return {}

    def upload_file(self, local_path, bucket, key, ExtraArgs=None):  # noqa: N803
        self.objects[key] = b"uploaded"
        return None

    def download_file(self, bucket, key, local_path):
        with open(local_path, "wb") as fh:
            fh.write(self.objects.get(key, b"fake-media-bytes"))
        return None

    def head_object(self, Bucket, Key):  # noqa: N803
        if Key in self.objects or Key.startswith("projects/"):
            return {}
        raise RuntimeError("NoSuchKey")

    def get_object(self, Bucket, Key):  # noqa: N803
        from io import BytesIO

        return {"Body": BytesIO(self.objects.get(Key, b""))}

    def delete_object(self, Bucket, Key):  # noqa: N803
        self.objects.pop(Key, None)
        return {}

    def delete_objects(self, Bucket, Delete):  # noqa: N803
        for obj in Delete.get("Objects", []):
            self.objects.pop(obj["Key"], None)
        return {}

    def get_paginator(self, _name):
        client = self

        class _Paginator:
            def paginate(self, Bucket, Prefix):  # noqa: N803
                keys = [k for k in client.objects if k.startswith(Prefix)]
                yield {"Contents": [{"Key": k} for k in keys]} if keys else {}

        return _Paginator()

    def generate_presigned_url(self, op, Params, ExpiresIn):  # noqa: N803
        return f"https://signed.test/{op}/{Params['Key']}?exp={ExpiresIn}"


@pytest.fixture(autouse=True)
def _external_fakes(monkeypatch: pytest.MonkeyPatch, fake_enqueue: AsyncMock) -> None:
    # --- queue -----------------------------------------------------------
    monkeypatch.setattr("app.workers.queue.enqueue", fake_enqueue, raising=False)
    monkeypatch.setattr(
        "app.services.project_service.enqueue", fake_enqueue, raising=False
    )

    # --- storage: patch only the boto3 client factory ----------------
    # The real app.services.storage code runs; it just talks to a fake client.
    fake_client = FakeS3Client()
    monkeypatch.setattr("app.services.storage.get_client", lambda: fake_client, raising=False)
    monkeypatch.setattr(
        "app.services.storage.get_presign_client", lambda: fake_client, raising=False
    )

    # --- SSRF: resolve every hostname to a fixed public IP ------------
    monkeypatch.setattr(
        "app.services.ssrf._resolve_addresses",
        lambda host: ["93.184.216.34"],
        raising=False,
    )

    # --- AI pipeline + ffmpeg ----------------------------------------
    monkeypatch.setattr("app.services.transcription.transcribe", _fake_transcribe, raising=False)
    monkeypatch.setattr("app.services.segmentation.detect_segments", _fake_detect_segments, raising=False)
    monkeypatch.setattr("app.services.rendering.render_clip", _fake_render_clip, raising=False)
    monkeypatch.setattr(
        "app.workers.pipeline._download_url",
        lambda url, dest: _fake_download_file("remote", dest) and None,
        raising=False,
    )

    # --- reset the in-process auth rate limiter ----------------------
    import app.routers.auth as auth_router

    auth_router._rate_buckets.clear()


# --------------------------------------------------------------------------- #
# Users / authenticated clients
# --------------------------------------------------------------------------- #
def _login(client: TestClient, email: str, password: str) -> str:
    resp = client.post(
        "/api/v1/auth/login", data={"username": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture
def auth_client(client: TestClient, db: Session) -> TestClient:
    """A registered + logged-in non-admin user, Authorization header set."""
    client.post(
        "/api/v1/auth/register",
        json={"email": "user@test.com", "password": "password123", "full_name": "User"},
    )
    token = _login(client, "user@test.com", "password123")
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def auth_user(db: Session, auth_client: TestClient) -> User:
    return db.query(User).filter(User.email == "user@test.com").one()


@pytest.fixture
def admin_user(db: Session) -> User:
    user = User(
        email="admin@test.com",
        hashed_password=hash_password("adminpass123"),
        full_name="Admin",
        is_active=True,
        is_verified=True,
        is_admin=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_client(client: TestClient, admin_user: User) -> TestClient:
    """A logged-in admin user, Authorization header set."""
    token = _login(client, "admin@test.com", "adminpass123")
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def make_user(client: TestClient, db: Session):
    """Factory: register a user, return (user_row, bearer_token)."""

    def _make(email: str, password: str = "password123") -> tuple[User, str]:
        client.post("/api/v1/auth/register", json={"email": email, "password": password})
        token = _login(client, email, password)
        user = db.query(User).filter(User.email == email).one()
        return user, token

    return _make
