import asyncio

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.db.session import engine
from app.services.github_service import GitHubService

# P0 regression: /auth/github/pat and /auth/github/callback are the login
# mechanism itself — they must be reachable with zero prior session. The bug
# was both routes depending on get_current_user, which hard-401s in
# production before the PAT/code is ever checked, making first login
# impossible. See app/api/deps.py:get_or_create_singleton_user.


@pytest.fixture(scope="module")
def client():
    # Dispose any connections the shared async engine pooled under a
    # different test module's event loop before this module claims its own
    # (asyncpg connections are bound to the loop that opened them).
    asyncio.run(engine.dispose())
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _production_environment():
    # The bug only manifests with ENVIRONMENT=production — in development,
    # get_current_user's auto-provision fallback masked it entirely.
    original = settings.ENVIRONMENT
    settings.ENVIRONMENT = "production"
    yield
    settings.ENVIRONMENT = original


def _fake_gh_user(login: str):
    return {
        "login": login,
        "id": 999999,
        "avatar_url": "https://example.com/avatar.png",
        "email": f"{login}@example.com",
    }


def test_pat_login_reachable_without_existing_session(client, monkeypatch):
    async def fake_verify_pat(token):
        assert token == "fake-valid-pat-1"
        return _fake_gh_user("octocat-test-1")

    monkeypatch.setattr(GitHubService, "verify_pat", staticmethod(fake_verify_pat))

    # Deliberately no Authorization header — this is the exact P0 scenario.
    resp = client.post(
        "/api/v1/auth/github/pat",
        json={"personal_access_token": "fake-valid-pat-1"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["access_token"]
    assert data["username"] == "octocat-test-1"


def test_invalid_pat_is_rejected(client, monkeypatch):
    async def fake_verify_pat_invalid(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="GitHub token verification failed: Bad credentials",
        )

    monkeypatch.setattr(GitHubService, "verify_pat", staticmethod(fake_verify_pat_invalid))

    resp = client.post(
        "/api/v1/auth/github/pat",
        json={"personal_access_token": "totally-invalid"},
    )
    assert resp.status_code == 401


def test_valid_pat_creates_usable_session(client, monkeypatch):
    async def fake_verify_pat(token):
        return _fake_gh_user("session-test-user")

    monkeypatch.setattr(GitHubService, "verify_pat", staticmethod(fake_verify_pat))

    login_resp = client.post(
        "/api/v1/auth/github/pat",
        json={"personal_access_token": "fake-valid-pat-2"},
    )
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]

    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "session-test-user"


def test_protected_routes_still_require_session_in_production(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401

    resp2 = client.get("/api/v1/repositories")
    assert resp2.status_code == 401


def test_oauth_callback_reachable_without_existing_session(client, monkeypatch):
    async def fake_exchange(code):
        assert code == "fake-code"
        return {"access_token": "fake-oauth-token", "scope": "repo,user"}

    async def fake_verify_pat(token):
        assert token == "fake-oauth-token"
        return _fake_gh_user("oauth-test-user")

    monkeypatch.setattr(GitHubService, "exchange_oauth_code", staticmethod(fake_exchange))
    monkeypatch.setattr(GitHubService, "verify_pat", staticmethod(fake_verify_pat))

    resp = client.post("/api/v1/auth/github/callback", json={"code": "fake-code"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["username"] == "oauth-test-user"


def test_oauth_url_endpoint_reachable_without_session(client):
    # No Authorization header — must never 401, it's needed before login.
    resp = client.get("/api/v1/auth/github/oauth-url")
    assert resp.status_code != 401
