import asyncio
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.db.session import engine
from app.models.repository import Repository
from app.models.monitoring import RepositoryEvent
from app.services.monitoring_service import (
    verify_github_signature,
    is_talos_branch,
    files_are_relevant,
    extract_changed_files,
    EventService,
    SchedulerService,
)

@pytest.fixture(scope="module")
def client():
    # Dispose any connections the shared async engine pooled under a different
    # test module's event loop before this module claims its own (asyncpg
    # connections are bound to the loop that opened them) — then use an
    # explicit context manager so one portal stays alive across every request
    # in this module.
    asyncio.run(engine.dispose())
    with TestClient(app) as c:
        yield c


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _push_payload(ref="refs/heads/main", full_name="acme/does-not-exist", files=None):
    return {
        "ref": ref,
        "after": "deadbeef",
        "repository": {"full_name": full_name},
        "commits": [{"id": "deadbeef", "added": files or [], "modified": [], "removed": []}],
    }


# ---- pure functions (no DB / no network) ----

def test_verify_github_signature_valid():
    body = b'{"a": 1}'
    assert verify_github_signature("mysecret", body, _sign("mysecret", body)) is True


def test_verify_github_signature_invalid():
    body = b'{"a": 1}'
    assert verify_github_signature("mysecret", body, _sign("wrong-secret", body)) is False


def test_verify_github_signature_missing_or_malformed_header():
    assert verify_github_signature("mysecret", b"{}", None) is False
    assert verify_github_signature("mysecret", b"{}", "") is False
    assert verify_github_signature("mysecret", b"{}", "not-sha256=abc") is False
    assert verify_github_signature("", b"{}", "sha256=abc") is False


def test_is_talos_branch():
    assert is_talos_branch("talos/fix-18-axios") is True
    assert is_talos_branch("main") is False
    assert is_talos_branch(None) is False


def test_files_are_relevant():
    assert files_are_relevant(["package.json"]) is True
    assert files_are_relevant(["backend/requirements.txt"]) is True
    assert files_are_relevant(["README.md", "docs/guide.md"]) is False
    assert files_are_relevant([]) is False


def test_extract_changed_files_from_commits():
    payload = {"commits": [{"added": ["a.txt"], "modified": ["package.json"], "removed": []}]}
    files = extract_changed_files(payload)
    assert "a.txt" in files and "package.json" in files


def test_extract_changed_files_falls_back_to_head_commit():
    payload = {"commits": [], "head_commit": {"added": [], "modified": ["requirements.txt"], "removed": []}}
    assert extract_changed_files(payload) == ["requirements.txt"]


def test_scheduler_due_check_respects_manual_schedule():
    repo = Repository(monitoring_schedule="manual", last_automatic_scan_at=None, last_scanned_at=None)
    assert SchedulerService._is_due(repo, datetime.now(timezone.utc)) is False


def test_scheduler_due_check_never_scanned_is_due():
    repo = Repository(monitoring_schedule="daily", last_automatic_scan_at=None, last_scanned_at=None)
    assert SchedulerService._is_due(repo, datetime.now(timezone.utc)) is True


def test_scheduler_due_check_recent_daily_scan_not_due():
    now = datetime.now(timezone.utc)
    repo = Repository(monitoring_schedule="daily", last_automatic_scan_at=now - timedelta(hours=2), last_scanned_at=None)
    assert SchedulerService._is_due(repo, now) is False


def test_scheduler_due_check_stale_daily_scan_is_due():
    now = datetime.now(timezone.utc)
    repo = Repository(monitoring_schedule="daily", last_automatic_scan_at=now - timedelta(hours=25), last_scanned_at=None)
    assert SchedulerService._is_due(repo, now) is True


def test_scheduler_due_check_weekly_schedule():
    now = datetime.now(timezone.utc)
    repo_recent = Repository(monitoring_schedule="weekly", last_automatic_scan_at=now - timedelta(days=2), last_scanned_at=None)
    repo_stale = Repository(monitoring_schedule="weekly", last_automatic_scan_at=now - timedelta(days=8), last_scanned_at=None)
    assert SchedulerService._is_due(repo_recent, now) is False
    assert SchedulerService._is_due(repo_stale, now) is True


# ---- webhook endpoint (real DB via TestClient, matching this repo's existing test style) ----

@pytest.fixture(autouse=True)
def _webhook_secret():
    original = settings.GITHUB_WEBHOOK_SECRET
    settings.GITHUB_WEBHOOK_SECRET = "test-webhook-secret"
    yield
    settings.GITHUB_WEBHOOK_SECRET = original


def test_webhook_rejects_missing_secret_config(client, monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_WEBHOOK_SECRET", "")
    body = json.dumps(_push_payload()).encode()
    resp = client.post(
        "/api/v1/webhooks/github", content=body,
        headers={"X-GitHub-Event": "push", "X-GitHub-Delivery": f"d-no-secret-{uuid.uuid4().hex}", "X-Hub-Signature-256": "sha256=irrelevant"},
    )
    assert resp.status_code == 503


def test_webhook_rejects_invalid_signature(client):
    body = json.dumps(_push_payload()).encode()
    resp = client.post(
        "/api/v1/webhooks/github", content=body,
        headers={"X-GitHub-Event": "push", "X-GitHub-Delivery": f"d-bad-sig-{uuid.uuid4().hex}", "X-Hub-Signature-256": "sha256=" + "0" * 64},
    )
    assert resp.status_code == 401


def test_webhook_accepts_valid_signature_for_unconnected_repo(client):
    body = json.dumps(_push_payload(full_name="acme/does-not-exist")).encode()
    sig = _sign(settings.GITHUB_WEBHOOK_SECRET, body)
    resp = client.post(
        "/api/v1/webhooks/github", content=body,
        headers={"X-GitHub-Event": "push", "X-GitHub-Delivery": f"d-valid-{uuid.uuid4().hex}", "X-Hub-Signature-256": sig},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"


def test_webhook_duplicate_delivery_ignored(client):
    body = json.dumps(_push_payload(full_name="acme/does-not-exist")).encode()
    sig = _sign(settings.GITHUB_WEBHOOK_SECRET, body)
    headers = {"X-GitHub-Event": "push", "X-GitHub-Delivery": f"d-dup-{uuid.uuid4().hex}", "X-Hub-Signature-256": sig}

    first = client.post("/api/v1/webhooks/github", content=body, headers=headers)
    second = client.post("/api/v1/webhooks/github", content=body, headers=headers)

    assert first.status_code == 200
    assert first.json()["status"] == "accepted"
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate_ignored"


def test_webhook_ignores_unrecognized_event_type(client):
    body = json.dumps({"zen": "keep it logically awesome."}).encode()
    sig = _sign(settings.GITHUB_WEBHOOK_SECRET, body)
    resp = client.post(
        "/api/v1/webhooks/github", content=body,
        headers={"X-GitHub-Event": "ping", "X-GitHub-Delivery": f"d-ping-{uuid.uuid4().hex}", "X-Hub-Signature-256": sig},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored_event_type"


def test_webhook_talos_branch_push_creates_skippable_event(client):
    """Section 29/60: TALOS's own patch-branch pushes must never start a new
    maintenance loop. The webhook layer accepts the event (still real
    auditability per section 53); the background handler is what actually
    skips it via is_talos_branch() — covered directly above."""
    body = json.dumps(_push_payload(ref="refs/heads/talos/fix-42-axios", full_name="acme/does-not-exist")).encode()
    sig = _sign(settings.GITHUB_WEBHOOK_SECRET, body)
    resp = client.post(
        "/api/v1/webhooks/github", content=body,
        headers={"X-GitHub-Event": "push", "X-GitHub-Delivery": f"d-talos-branch-{uuid.uuid4().hex}", "X-Hub-Signature-256": sig},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"
