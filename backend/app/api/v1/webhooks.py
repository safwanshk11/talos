import json
import logging

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import Depends

from app.db.session import get_db
from app.core.config import settings
from app.models.repository import Repository
from app.services.monitoring_service import (
    EventService,
    MonitoringOrchestrator,
    verify_github_signature,
    extract_changed_files,
)

logger = logging.getLogger("talos.webhooks")
router = APIRouter()

# Section 52: bounded payload size — GitHub webhooks are small; reject anything
# grossly oversized before even parsing it.
MAX_PAYLOAD_BYTES = 2 * 1024 * 1024


@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(default=""),
    x_github_delivery: str = Header(default=""),
    x_hub_signature_256: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
):
    """Section 12-13: trusted GitHub event intake. Signature-verified before
    any processing; its only job is receive -> validate -> normalize -> queue.
    The actual scan/patch work happens in a background task with its own DB
    session, decoupled from this request (section 41)."""
    body = await request.body()
    if len(body) > MAX_PAYLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Payload too large.")

    if not settings.GITHUB_WEBHOOK_SECRET:
        # Refuse rather than silently accept unverifiable requests.
        raise HTTPException(status_code=503, detail="Webhook secret not configured.")

    if not verify_github_signature(settings.GITHUB_WEBHOOK_SECRET, body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature.")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    if not x_github_event:
        raise HTTPException(status_code=400, detail="Missing X-GitHub-Event header.")

    # Idempotency (section 16) — GitHub may retry delivery.
    if await EventService.is_duplicate_delivery(db, x_github_delivery or None):
        return {"status": "duplicate_ignored"}

    full_name = (payload.get("repository") or {}).get("full_name")
    repo = None
    if full_name:
        stmt = select(Repository).where(Repository.full_name == full_name, Repository.connection_status != "disconnected")
        repo = (await db.execute(stmt)).scalars().first()

    if x_github_event == "push":
        ref = payload.get("ref")
        commit_sha = payload.get("after")
        branch = ref.split("refs/heads/")[-1] if ref and ref.startswith("refs/heads/") else ref
        changed_files = extract_changed_files(payload)

        event = await EventService.record(
            db, provider="github", event_type="push", delivery_id=x_github_delivery or None,
            repository_id=repo.id if repo else None, branch=branch, commit_sha=commit_sha,
            metadata={"full_name": full_name, "changed_files": changed_files[:50]},
        )
        background_tasks.add_task(MonitoringOrchestrator.process_push_event, event.id)
        return {"status": "accepted", "event_id": event.id}

    if x_github_event == "pull_request":
        await EventService.record(
            db, provider="github", event_type="pull_request", delivery_id=x_github_delivery or None,
            repository_id=repo.id if repo else None, branch=None, commit_sha=None,
            metadata={"full_name": full_name, "action": payload.get("action")},
        )
        background_tasks.add_task(MonitoringOrchestrator.process_pull_request_event, payload, repo.id if repo else None)
        return {"status": "accepted"}

    # Section 4: don't react to every possible event — acknowledge and ignore.
    return {"status": "ignored_event_type", "event_type": x_github_event}
