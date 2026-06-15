"""
Backend API gating and authentication tests.

Tests cover:
- File upload validation (type, size)
- API key enforcement on write endpoints
- Destructive endpoint gating
- Debug endpoint gating
- Localization endpoint auth

These tests use FastAPI's TestClient and override get_settings() / get_db()
so no real database or Celery worker is required.
"""
from __future__ import annotations

import io
import json
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# ─── App under test ────────────────────────────────────────────────────────────
from backend.api.main import app
from backend.utils.config import Settings, get_settings
from backend.utils.db import get_db

# ─── Helpers ───────────────────────────────────────────────────────────────────

FAKE_API_KEY = "test-secret-key-123456789abcdef"


def _make_settings(**overrides) -> Settings:
    """Return a Settings instance with safe test defaults, optionally overridden."""
    base = dict(
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/0",
        storage_backend="LOCAL",
        colmap_bin="colmap",
        ffmpeg_bin="ffmpeg",
        api_key=None,
        allow_debug_endpoints=True,
        allow_destructive_endpoints=True,
        max_upload_size_mb=100,
    )
    base.update(overrides)
    return Settings.model_construct(**base)


def _override_settings(settings: Settings):
    """Return a dependency-override callable for get_settings."""
    def _inner():
        return settings
    return _inner


def _fake_db() -> Generator[MagicMock, None, None]:
    """Yield a MagicMock session that mimics SQLAlchemy Session."""
    db = MagicMock(spec=Session)
    # make db.get() return None by default (scene not found) unless overridden in test
    db.get.return_value = None
    db.scalar.return_value = 0
    db.scalars.return_value.all.return_value = []
    yield db


def _make_video_bytes(size_bytes: int = 1024) -> bytes:
    """Return fake bytes that pass content-type sniffing as an mp4."""
    return b"\x00\x00\x00\x18ftypisom" + b"\x00" * (size_bytes - 8)


def _make_image_bytes() -> bytes:
    """Return a minimal valid JPEG header."""
    return bytes(
        [0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01]
        + [0x00] * 100
    )


# ─── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def override_db():
    """Always replace the real DB session with a mock for every test."""
    app.dependency_overrides[get_db] = _fake_db
    yield
    app.dependency_overrides.pop(get_db, None)


def _make_client(settings) -> Generator[TestClient, None, None]:
    """Create a TestClient with settings overridden and DB / lifespan mocked."""
    app.dependency_overrides[get_settings] = _override_settings(settings)
    # Patch init_db (lifespan startup) and the async persistence loop so the
    # TestClient never touches a real Postgres server.
    with (
        patch("backend.api.main.init_db"),
        patch("backend.api.main.persist_agent_states_loop", return_value=_noop_coro()),
        patch("backend.utils.db._get_engine"),
    ):
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c
    app.dependency_overrides.pop(get_settings, None)


async def _noop_coro():
    """Async no-op coroutine used to replace the persistence background loop."""


@pytest.fixture()
def client_no_auth() -> Generator[TestClient, None, None]:
    """TestClient with no api_key enforced (default local dev behaviour)."""
    yield from _make_client(_make_settings(api_key=None))


@pytest.fixture()
def client_with_auth() -> Generator[TestClient, None, None]:
    """TestClient with api_key enforced."""
    yield from _make_client(_make_settings(api_key=FAKE_API_KEY))


@pytest.fixture()
def client_no_destructive() -> Generator[TestClient, None, None]:
    """TestClient with destructive endpoints disabled, no api_key required."""
    yield from _make_client(_make_settings(api_key=None, allow_destructive_endpoints=False))


@pytest.fixture()
def client_no_debug() -> Generator[TestClient, None, None]:
    """TestClient with debug endpoints disabled."""
    yield from _make_client(_make_settings(api_key=None, allow_debug_endpoints=False))


# ─── Upload validation tests ───────────────────────────────────────────────────

class TestUploadValidation:
    @patch("backend.workers.tasks.process_scene_task.delay")
    @patch("backend.utils.storage.LocalStorageProvider.save_file", return_value="/tmp/fake.mp4")
    def test_valid_mp4_no_auth_required(self, _save, _task, client_no_auth):
        """A valid mp4 upload passes when no API key is required."""
        data = _make_video_bytes(512)
        response = client_no_auth.post(
            "/scene/upload",
            files={"file": ("test.mp4", io.BytesIO(data), "video/mp4")},
            data={"name": "test-scene"},
        )
        # 200 or 500 due to mocked DB — we just confirm it's not 415/413/401
        assert response.status_code not in (401, 413, 415), response.text

    def test_unsupported_extension_returns_415(self, client_no_auth):
        """An unsupported file extension (.xyz) must return HTTP 415."""
        response = client_no_auth.post(
            "/scene/upload",
            files={"file": ("model.xyz", io.BytesIO(b"garbage"), "application/octet-stream")},
        )
        assert response.status_code == 415
        assert "Unsupported" in response.json()["detail"]

    def test_file_too_large_returns_413(self, client_no_auth):
        """A file exceeding max_upload_size_mb must return HTTP 413."""
        # max is 100 MB in fixture; send slightly more via Content-Length hint
        # FastAPI reads file.size from UploadFile.size which comes from Content-Length
        big_data = b"\x00" * (101 * 1024 * 1024)
        response = client_no_auth.post(
            "/scene/upload",
            files={"file": ("big.mp4", io.BytesIO(big_data), "video/mp4")},
        )
        # 413 expected
        assert response.status_code == 413
        assert "too large" in response.json()["detail"]

    def test_upload_without_api_key_returns_401_when_required(self, client_with_auth):
        """When api_key is set, upload without header must return 401."""
        data = _make_video_bytes(512)
        response = client_with_auth.post(
            "/scene/upload",
            files={"file": ("test.mp4", io.BytesIO(data), "video/mp4")},
            # no X-API-Key header
        )
        assert response.status_code == 401

    @patch("backend.workers.tasks.process_scene_task.delay")
    @patch("backend.utils.storage.LocalStorageProvider.save_file", return_value="/tmp/fake.mp4")
    def test_upload_with_correct_api_key_passes_auth(self, _save, _task, client_with_auth):
        """Upload with correct X-API-Key header passes auth check."""
        data = _make_video_bytes(512)
        response = client_with_auth.post(
            "/scene/upload",
            files={"file": ("test.mp4", io.BytesIO(data), "video/mp4")},
            headers={"X-API-Key": FAKE_API_KEY},
        )
        # Auth passes — downstream may fail due to mock DB (not 401/415/413)
        assert response.status_code not in (401, 415, 413), response.text

    def test_upload_with_wrong_api_key_returns_401(self, client_with_auth):
        """Upload with wrong X-API-Key must return 401."""
        data = _make_video_bytes(512)
        response = client_with_auth.post(
            "/scene/upload",
            files={"file": ("test.mp4", io.BytesIO(data), "video/mp4")},
            headers={"X-API-Key": "wrong-key"},
        )
        assert response.status_code == 401


# ─── Process endpoint tests ────────────────────────────────────────────────────

class TestProcessEndpoint:
    def test_process_without_api_key_returns_401_when_required(self, client_with_auth):
        """POST /scene/{id}/process without header returns 401 when key is set."""
        response = client_with_auth.post("/scene/some-scene-id/process")
        assert response.status_code == 401

    @patch("backend.workers.tasks.process_scene_task.delay")
    def test_process_with_api_key_passes_auth(self, _task, client_with_auth):
        """POST /scene/{id}/process with correct key passes auth (may 404 on mock DB)."""
        response = client_with_auth.post(
            "/scene/some-scene-id/process",
            headers={"X-API-Key": FAKE_API_KEY},
        )
        assert response.status_code != 401


# ─── Destructive endpoint tests ────────────────────────────────────────────────

class TestDestructiveEndpoints:
    def test_cleanup_returns_403_when_destructive_disabled(self, client_no_destructive):
        """DELETE /scene/{id}/cleanup returns 403 when allow_destructive_endpoints=False."""
        response = client_no_destructive.delete("/scene/some-scene-id/cleanup")
        assert response.status_code == 403
        assert "Destructive endpoints are disabled" in response.json()["detail"]

    def test_delete_anchor_returns_403_when_destructive_disabled(self, client_no_destructive):
        """DELETE /scene/{id}/anchors/{anchor_id} returns 403 when disabled."""
        response = client_no_destructive.delete("/scene/some-scene-id/anchors/some-anchor-id")
        assert response.status_code == 403


# ─── Debug endpoint tests ──────────────────────────────────────────────────────

class TestDebugEndpoints:
    def test_debug_path_returns_403_when_debug_disabled(self, client_no_debug):
        """GET /debug-path returns 403 when allow_debug_endpoints=False."""
        response = client_no_debug.get("/debug-path")
        assert response.status_code == 403
        assert "Debug endpoints are disabled" in response.json()["detail"]

    def test_debug_path_returns_200_when_enabled(self, client_no_auth):
        """GET /debug-path returns 200 when allow_debug_endpoints=True."""
        response = client_no_auth.get("/debug-path")
        assert response.status_code == 200
        assert "storage_root" in response.json()


# ─── Localize endpoint tests ───────────────────────────────────────────────────

class TestLocalizeEndpoint:
    def test_localize_without_api_key_returns_401_when_required(self, client_with_auth):
        """POST /vps/localize without header returns 401 when key is required."""
        image_bytes = _make_image_bytes()
        response = client_with_auth.post(
            "/vps/localize",
            data={"scene_id": "some-scene"},
            files={"query_image": ("frame.jpg", io.BytesIO(image_bytes), "image/jpeg")},
        )
        assert response.status_code == 401

    def test_localize_without_api_key_passes_when_not_required(self, client_no_auth):
        """POST /vps/localize without header passes auth when no key is configured."""
        image_bytes = _make_image_bytes()
        # Will fail downstream (404 scene) but not 401
        response = client_no_auth.post(
            "/vps/localize",
            data={"scene_id": "some-scene"},
            files={"query_image": ("frame.jpg", io.BytesIO(image_bytes), "image/jpeg")},
        )
        assert response.status_code != 401

    def test_health_check_always_passes(self, client_with_auth):
        """GET /health is always accessible regardless of auth config."""
        response = client_with_auth.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
