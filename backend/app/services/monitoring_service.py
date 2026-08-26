"""Phase 7: Continuous Autonomous Monitoring & Event-Driven Maintenance.

TALOS watches continuously, acts selectively. This module is the layer between
"something happened" (a GitHub webhook, a scheduled tick) and the existing,
unmodified Phase 2-6.5 pipeline (scan -> detect -> Decision Engine -> patch ->
verify -> deliver). It never bypasses the Decision Engine and never invents a
second autonomous pipeline — it only decides *whether* and *when* to invoke
the one that already exists.
"""

import hashlib
import hmac
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.repository import Repository
from app.models.scan import RepositoryScan
from app.models.future import MaintenanceIssue, MaintenanceJob, PatchAttempt, ActionLog
from app.models.monitoring import RepositoryEvent
from app.services.repository_service import RepositoryService
from app.services.scanner_service import ScannerService
from app.services.patch_service import PatchService
from app.services.git_workspace_service import GitWorkspaceService

logger = logging.getLogger("talos.monitoring")

# Section 6: files whose change can genuinely invalidate previously-scanned
# repository intelligence. Deliberately narrow — not every file, not docs.
RELEVANT_FILE_BASENAMES = {
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "requirements.txt", "pyproject.toml", "poetry.lock",
}

# Jobs/scans in these states are genuinely doing work — used for the
# "existing active scan/job" dedup checks (sections 17-19).
ACTIVE_SCAN_STATUSES = ["queued", "running"]
ACTIVE_JOB_STATUSES = ["analyzing", "planning", "planned", "sandboxing", "patching", "verifying", "delivering"]

SCHEDULE_INTERVALS = {
    "daily": timedelta(hours=24),
    "weekly": timedelta(days=7),
}

TRIGGER_SCHEDULED_SCAN = "scheduled_scan"
TRIGGER_GITHUB_PUSH = "github_push"
TRIGGER_MANUAL = "manual"


def verify_github_signature(secret: str, payload_body: bytes, signature_header: Optional[str]) -> bool:
    """Section 13: verify X-Hub-Signature-256. Never trust a payload just
    because it looks like GitHub's shape."""
    if not secret or not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), payload_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def is_talos_branch(branch: Optional[str]) -> bool:
    """Section 29: loop prevention — never react to TALOS's own patch pushes."""
    return bool(branch) and branch.startswith(f"{PatchService.BRANCH_PREFIX}-")


def extract_changed_files(push_payload: Dict[str, Any]) -> List[str]:
    files: List[str] = []
    for commit in push_payload.get("commits", []) or []:
        files.extend(commit.get("added", []) or [])
        files.extend(commit.get("modified", []) or [])
        files.extend(commit.get("removed", []) or [])
    if not files and push_payload.get("head_commit"):
        hc = push_payload["head_commit"]
        files.extend(hc.get("added", []) or [])
        files.extend(hc.get("modified", []) or [])
        files.extend(hc.get("removed", []) or [])
    return files


def files_are_relevant(changed_files: List[str]) -> bool:
    return any(f.rsplit("/", 1)[-1] in RELEVANT_FILE_BASENAMES for f in changed_files)


class EventService:
    @staticmethod
    async def is_duplicate_delivery(db: AsyncSession, delivery_id: Optional[str]) -> bool:
        """Section 16: GitHub may retry delivery. One push must never become
        two scans."""
        if not delivery_id:
            return False
        stmt = select(RepositoryEvent).where(RepositoryEvent.delivery_id == delivery_id)
        existing = (await db.execute(stmt)).scalars().first()
        return existing is not None

    @staticmethod
    async def record(
        db: AsyncSession, provider: str, event_type: str, delivery_id: Optional[str],
        repository_id: Optional[int], branch: Optional[str], commit_sha: Optional[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RepositoryEvent:
        event = RepositoryEvent(
            repository_id=repository_id, provider=provider, event_type=event_type,
            delivery_id=delivery_id, branch=branch, commit_sha=commit_sha,
            status="received", event_metadata=metadata or {},
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event

    @staticmethod
    async def mark(db: AsyncSession, event: RepositoryEvent, status: str, skip_reason: Optional[str] = None, scan_id: Optional[int] = None):
        event.status = status
        event.skip_reason = skip_reason
        event.triggered_scan_id = scan_id
        event.processed_at = datetime.now(timezone.utc)
        await db.commit()


class MonitoringOrchestrator:
    """Reuses the existing scan -> detect -> Decision Engine -> patch pipeline
    unmodified (sections 20-21) — this class only decides whether to invoke it
    and records why."""

    @staticmethod
    async def _log(db: AsyncSession, repository_id: int, step: str, message: str, level: str = "INFO"):
        entry = ActionLog(repository_id=repository_id, step=step, message=message, level=level, timestamp=datetime.now(timezone.utc))
        db.add(entry)
        await db.commit()

    @staticmethod
    async def has_active_scan(db: AsyncSession, repository_id: int) -> bool:
        stmt = select(RepositoryScan.id).where(RepositoryScan.repository_id == repository_id, RepositoryScan.status.in_(ACTIVE_SCAN_STATUSES))
        return (await db.execute(stmt)).scalars().first() is not None

    @staticmethod
    async def has_active_job(db: AsyncSession, repository_id: int) -> bool:
        """Section 19: preserve Phase 6.5 repository-level collision safety —
        one mutating maintenance workflow per repository at a time."""
        stmt = select(MaintenanceJob.id).where(MaintenanceJob.repository_id == repository_id, MaintenanceJob.status.in_(ACTIVE_JOB_STATUSES))
        return (await db.execute(stmt)).scalars().first() is not None

    @staticmethod
    async def run_autonomous_cycle(db: AsyncSession, repo: Repository, trigger: str) -> Dict[str, Any]:
        """Scan the repository, then — if the scan is clean of active-job
        conflicts — let the highest-severity OPEN issue pass through the
        existing Decision-Engine-gated prepare_fix. Every other OPEN issue is
        left for the next cycle rather than spamming N conflict-blocked jobs
        in the same tick (section 46: cost/waste awareness)."""
        result: Dict[str, Any] = {"scan_id": None, "job_id": None, "reason": None}

        if await MonitoringOrchestrator.has_active_scan(db, repo.id):
            result["reason"] = "scan_already_active"
            return result
        if await MonitoringOrchestrator.has_active_job(db, repo.id):
            result["reason"] = "job_already_active"
            return result

        try:
            token = await RepositoryService.get_user_github_token(db, repo.user_id)
        except Exception as exc:
            result["reason"] = f"github_token_unavailable: {exc}"
            return result

        await MonitoringOrchestrator._log(db, repo.id, "WATCH", f"Autonomous cycle started (trigger={trigger}).")

        try:
            scan = await ScannerService.run_repository_scan(db, repo.user_id, repo.id, token, trigger=trigger)
        except Exception as exc:
            logger.warning(f"Autonomous scan failed for repository {repo.id}: {exc}")
            result["reason"] = f"scan_failed: {exc}"
            return result

        result["scan_id"] = scan.id
        repo.last_automatic_scan_at = datetime.now(timezone.utc)
        repo.last_trigger = trigger
        await db.commit()

        if scan.status != "completed":
            result["reason"] = "scan_did_not_complete"
            return result

        stmt = (
            select(MaintenanceIssue)
            .where(MaintenanceIssue.repository_id == repo.id, MaintenanceIssue.status == "OPEN")
            .order_by(MaintenanceIssue.severity)
        )
        open_issues = (await db.execute(stmt)).scalars().all()
        if not open_issues:
            result["reason"] = "no_open_issues"
            return result

        severity_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}
        target_issue = sorted(open_issues, key=lambda i: severity_rank.get(i.severity, 4))[0]

        await MonitoringOrchestrator._log(
            db, repo.id, "WATCH",
            f"New/open issue selected for autonomous evaluation: {target_issue.package_name or target_issue.title} ({target_issue.severity})."
        )

        try:
            job = await PatchService.prepare_fix(db, repo.user_id, repo.id, target_issue.id, token, trigger=trigger)
            result["job_id"] = job.id
            result["reason"] = f"prepare_fix_dispatched:{job.decision or job.status}"
        except Exception as exc:
            logger.warning(f"Autonomous prepare_fix failed for repository {repo.id}, issue {target_issue.id}: {exc}")
            result["reason"] = f"prepare_fix_failed: {exc}"

        return result

    @staticmethod
    async def process_push_event(event_id: int):
        """Runs as a background task — opens its own DB session since the
        request that received the webhook has already returned a response
        (section 41: background execution, not tied to any open browser/request)."""
        async with AsyncSessionLocal() as db:
            stmt = select(RepositoryEvent).where(RepositoryEvent.id == event_id)
            event = (await db.execute(stmt)).scalars().first()
            if not event:
                return

            if not event.repository_id:
                await EventService.mark(db, event, "skipped", "repository_not_connected")
                return

            stmt_repo = select(Repository).where(Repository.id == event.repository_id)
            repo = (await db.execute(stmt_repo)).scalars().first()
            if not repo or repo.connection_status == "disconnected":
                await EventService.mark(db, event, "skipped", "repository_not_connected")
                return

            if repo.monitoring_status == "paused":
                await EventService.mark(db, event, "skipped", "repository_paused")
                return

            if is_talos_branch(event.branch):
                await EventService.mark(db, event, "skipped", "talos_generated_branch")
                return

            if event.branch and event.branch != repo.default_branch:
                await EventService.mark(db, event, "skipped", "non_default_branch")
                return

            if not repo.scan_on_relevant_push:
                await EventService.mark(db, event, "skipped", "push_scanning_disabled")
                return

            changed_files = (event.event_metadata or {}).get("changed_files", [])
            if not files_are_relevant(changed_files):
                await EventService.mark(db, event, "skipped", "no_relevant_file_changes")
                return

            cycle = await MonitoringOrchestrator.run_autonomous_cycle(db, repo, trigger=TRIGGER_GITHUB_PUSH)
            if cycle["scan_id"]:
                await EventService.mark(db, event, "processed", cycle["reason"], scan_id=cycle["scan_id"])
            else:
                await EventService.mark(db, event, "skipped", cycle["reason"])

    @staticmethod
    async def process_pull_request_event(payload: Dict[str, Any], repository_id: Optional[int]):
        """Section 30-31: keep TALOS's own PullRequest.github_status in sync
        with real GitHub state on close/merge — never re-creates or reopens
        a PR a human closed."""
        if not repository_id:
            return
        action = payload.get("action")
        if action != "closed":
            return

        pr_payload = payload.get("pull_request", {})
        head_ref = (pr_payload.get("head") or {}).get("ref")
        merged = bool(pr_payload.get("merged"))
        if not head_ref:
            return

        async with AsyncSessionLocal() as db:
            from app.models.future import PullRequest
            stmt = (
                select(PullRequest)
                .where(PullRequest.repository_id == repository_id, PullRequest.head_branch == head_ref)
                .order_by(desc(PullRequest.created_at))
            )
            pr = (await db.execute(stmt)).scalars().first()
            if not pr:
                return
            pr.github_status = "merged" if merged else "closed"
            await db.commit()
            await MonitoringOrchestrator._log(
                db, repository_id, "DELIVER",
                f"GitHub reports pull request #{pr.pr_number} {'merged' if merged else 'closed without merge'}.",
            )


class WorkspaceReaperService:
    """Phase 8 section 14: patch workspaces (isolated git clones on the shared
    `talos_workspaces` volume) are kept on disk for as long as a job might still
    need them — a pending approval, a not-yet-clicked manual Verify/Deliver.
    Nothing previously reclaimed them once a job was genuinely done, so they
    accumulated forever. This reaps them on a delay long enough that a human
    reviewing a demo-day result still has the workspace available, without
    keeping every clone since the app's first run.

    Only PatchAttempt.workspace_path is cleared — patch_diff, analysis, plan,
    and every other persisted field on the attempt/job are untouched, so the
    audit trail and diff viewer keep working after a workspace is reaped."""

    @staticmethod
    async def reap(db: AsyncSession) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.WORKSPACE_RETENTION_HOURS)
        not_reapable = set(ACTIVE_JOB_STATUSES) | {"waiting_for_approval"}

        stmt = (
            select(PatchAttempt, MaintenanceJob)
            .join(MaintenanceJob, PatchAttempt.job_id == MaintenanceJob.id)
            .where(PatchAttempt.workspace_path.isnot(None))
            .where(MaintenanceJob.status.notin_(not_reapable))
        )
        rows = (await db.execute(stmt)).all()

        reaped = 0
        for attempt, job in rows:
            last_activity = job.completed_at or job.created_at
            if last_activity and last_activity > cutoff:
                continue
            GitWorkspaceService.cleanup(attempt.workspace_path)
            attempt.workspace_path = None
            reaped += 1

        if reaped:
            await db.commit()
        return reaped


class SchedulerService:
    """Section 7-9, 42: the simplest deployment-compatible scheduler — an
    asyncio background task inside the existing backend process. No new
    infrastructure (no Celery/Redis/cron daemon) — matches this codebase's
    established "simplest reliable mechanism" precedent from Phase 6's polling."""

    @staticmethod
    def _is_due(repo: Repository, now: datetime) -> bool:
        if repo.monitoring_schedule not in SCHEDULE_INTERVALS:
            return False
        interval = SCHEDULE_INTERVALS[repo.monitoring_schedule]
        last = repo.last_automatic_scan_at or repo.last_scanned_at
        if not last:
            return True
        return now - last >= interval

    @staticmethod
    async def tick():
        async with AsyncSessionLocal() as db:
            stmt = select(Repository).where(Repository.connection_status != "disconnected", Repository.monitoring_status == "active")
            repos = (await db.execute(stmt)).scalars().all()
            now = datetime.now(timezone.utc)
            due = [r for r in repos if SchedulerService._is_due(r, now)]

            for repo in due:
                event = await EventService.record(
                    db, provider="talos", event_type="scheduled_scan", delivery_id=None,
                    repository_id=repo.id, branch=None, commit_sha=None,
                    metadata={"schedule": repo.monitoring_schedule},
                )
                try:
                    cycle = await MonitoringOrchestrator.run_autonomous_cycle(db, repo, trigger=TRIGGER_SCHEDULED_SCAN)
                    if cycle["scan_id"]:
                        await EventService.mark(db, event, "processed", cycle["reason"], scan_id=cycle["scan_id"])
                    else:
                        await EventService.mark(db, event, "skipped", cycle["reason"])
                except Exception as exc:
                    logger.exception(f"Scheduled cycle failed for repository {repo.id}")
                    await EventService.mark(db, event, "failed", str(exc))

            try:
                reaped = await WorkspaceReaperService.reap(db)
                if reaped:
                    logger.info(f"Workspace reaper: reclaimed {reaped} stale patch workspace(s).")
            except Exception:
                logger.exception("Workspace reaper tick failed.")
