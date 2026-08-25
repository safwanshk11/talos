import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from app.models.repository import Repository
from app.models.future import (
    MaintenanceJob,
    MaintenanceIssue,
    PatchAttempt,
    VerificationRun,
    VerificationCheck,
    PullRequest,
    ActionLog,
)
from app.services.git_workspace_service import GitWorkspaceService, GitWorkspaceError
from app.services.github_service import GitHubService

logger = logging.getLogger("talos.delivery")

PROTECTED_BRANCHES = {"main", "master"}

CHECK_LABELS = {
    "INSTALL": "Install Dependencies",
    "BUILD": "Build",
    "TYPECHECK": "Type Check",
    "LINT": "Lint",
    "TEST": "Tests",
    "SECURITY_AUDIT": "Security Audit",
    "VULNERABILITY_RESCAN": "Original Vulnerability",
}


class DeliveryError(Exception):
    pass


class DeliveryService:
    """Phase 5 orchestrator: VERIFIED -> deliver the exact verified artifact as a
    real, review-ready GitHub pull request.

    Never invokes an AIProvider and never regenerates the patch — the diff that
    gets pushed is byte-identical to the one Phase 4 verified (enforced by the
    artifact-hash check below), and TALOS never merges what it creates.
    """

    @staticmethod
    async def _log(db: AsyncSession, job_id: Optional[int], repository_id: int, step: str, message: str, level: str = "INFO"):
        entry = ActionLog(
            repository_id=repository_id, job_id=job_id, step=step, message=message,
            level=level, timestamp=datetime.now(timezone.utc),
        )
        db.add(entry)
        await db.commit()

    # ------------------------------------------------------------------ entrypoint

    @staticmethod
    async def deliver(db: AsyncSession, user_id: int, repository_id: int, job_id: int, token: str) -> PullRequest:
        repo = await DeliveryService._get_repository(db, user_id, repository_id)
        job = await DeliveryService._get_job(db, repository_id, job_id)
        issue = await DeliveryService._get_issue(db, job.issue_id)

        # -------------------------------------------------- idempotency (checked before the
        # gate below, since a successful delivery advances job.status to "delivered", which
        # would otherwise fail the gate on a second click / duplicate request)
        existing_pr = await DeliveryService._get_existing_pull_request(db, job.id)
        if existing_pr and existing_pr.status == "delivered" and existing_pr.pr_number:
            return existing_pr

        # -------------------------------------------------- hard delivery gate
        # "verified" is the normal entrypoint; "delivering"/"delivery_failed" are
        # allowed so a retry after a partial failure can resume rather than being
        # locked out because job.status already moved off "verified".
        if job.status not in ("verified", "delivering", "delivery_failed"):
            raise HTTPException(
                status_code=400,
                detail="DELIVERY BLOCKED: this maintenance job is not VERIFIED. "
                       "Only a genuinely verified patch may be delivered.",
            )

        attempt = await DeliveryService._get_latest_ready_attempt(db, job.id)
        if not attempt:
            raise HTTPException(status_code=400, detail="DELIVERY BLOCKED: no ready patch attempt found for this job.")

        run = await DeliveryService._get_latest_verified_run(db, attempt.id)
        if not run:
            raise HTTPException(
                status_code=400,
                detail="DELIVERY BLOCKED: no successful VerificationRun exists for this patch attempt.",
            )

        # `run.status == "verified"` already encodes VerificationService's required-vs-optional
        # distinction (e.g. an unrelated optional SECURITY_AUDIT failure doesn't block VERIFIED) —
        # re-deriving pass/fail from individual check rows here would contradict that verdict.
        checks = await DeliveryService._get_checks(db, run.id)

        if not attempt.workspace_path or not os.path.isdir(attempt.workspace_path):
            raise HTTPException(
                status_code=400,
                detail="The verified workspace is no longer available (e.g. after an infra restart). "
                       "Run Prepare Fix and Run Verification again before delivering.",
            )

        # -------------------------------------------------- partial-delivery recovery
        # (the "already delivered" case was handled above, before the gate)
        pr = existing_pr
        if not pr:
            pr = PullRequest(
                repository_id=repository_id,
                maintenance_job_id=job.id,
                patch_attempt_id=attempt.id,
                verification_run_id=run.id,
                status="pending",
            )
            db.add(pr)
            await db.commit()
            await db.refresh(pr)

        job.status = "delivering"
        await db.commit()
        await DeliveryService._log(db, job.id, repository_id, "DELIVER", f"Delivery requested for job #{job.id}.")

        try:
            # -------------------------------------------------- branch safety
            current_branch = GitWorkspaceService.get_current_branch(attempt.workspace_path)
            if current_branch != attempt.branch_name or current_branch in PROTECTED_BRANCHES or current_branch == repo.default_branch:
                raise DeliveryError(
                    f"Workspace branch mismatch: expected TALOS branch '{attempt.branch_name}', found '{current_branch}'."
                )
            head_sha = GitWorkspaceService.get_head_sha(attempt.workspace_path)
            if head_sha != attempt.commit_sha:
                raise DeliveryError(
                    "Workspace HEAD no longer matches the verified commit. Re-verification required."
                )

            # -------------------------------------------------- artifact integrity
            verification_hash = hashlib.sha256((attempt.patch_diff or "").encode("utf-8")).hexdigest()
            current_diff = (
                GitWorkspaceService.diff_against_sha(attempt.workspace_path, attempt.base_sha)
                if attempt.base_sha else attempt.patch_diff
            )
            delivery_hash = hashlib.sha256((current_diff or "").encode("utf-8")).hexdigest()
            pr.verification_artifact_hash = verification_hash
            pr.delivery_artifact_hash = delivery_hash
            await db.commit()

            if verification_hash != delivery_hash:
                raise DeliveryError("Patch changed after verification. Re-verification required.")

            await DeliveryService._log(db, job.id, repository_id, "DELIVER", "Verified artifact integrity confirmed.")

            # -------------------------------------------------- commit (reuse Phase 3's exact commit)
            pr.status = "committing"
            pr.commit_sha = attempt.commit_sha
            pr.head_branch = attempt.branch_name
            pr.base_branch = repo.default_branch
            await db.commit()
            await DeliveryService._log(
                db, job.id, repository_id, "DELIVER",
                f"Reusing verified commit {attempt.commit_sha[:10] if attempt.commit_sha else '?'} "
                f"(no new commit created — the exact verified artifact is delivered).",
            )

            # -------------------------------------------------- push
            pr.status = "pushing"
            await db.commit()

            authed_url = repo.clone_url
            if token and "github.com" in repo.clone_url:
                authed_url = repo.clone_url.replace("https://github.com/", f"https://x-access-token:{token}@github.com/")

            try:
                GitWorkspaceService.push_branch(attempt.workspace_path, authed_url, attempt.branch_name, token=token)
            except GitWorkspaceError as exc:
                raise DeliveryError(f"Failed to push TALOS branch to GitHub: {exc}") from exc

            await DeliveryService._log(db, job.id, repository_id, "DELIVER", f"TALOS branch '{attempt.branch_name}' pushed.")

            # -------------------------------------------------- create (or reuse) the pull request
            pr.status = "creating_pr"
            await db.commit()
            await DeliveryService._log(db, job.id, repository_id, "DELIVER", "Creating GitHub pull request...")

            existing_gh_pr = await GitHubService.find_pull_request_by_head(token, repo.owner, repo.name, attempt.branch_name)
            if existing_gh_pr:
                gh_pr = existing_gh_pr
            else:
                title, body = await DeliveryService._build_pr_content(db, issue, attempt, run, checks, job)
                pr.title = title
                gh_pr = await GitHubService.create_pull_request(
                    token, repo.owner, repo.name, title, attempt.branch_name, repo.default_branch, body
                )

            pr.pr_number = gh_pr.get("number")
            pr.pr_url = gh_pr.get("html_url")
            pr.github_status = "merged" if gh_pr.get("merged") else gh_pr.get("state", "open")
            if not pr.title:
                pr.title = gh_pr.get("title")
            pr.status = "delivered"
            await db.commit()

            job.status = "delivered"
            job.completed_at = datetime.now(timezone.utc)
            if issue:
                issue.status = "DELIVERED"
            await db.commit()

            await DeliveryService._log(
                db, job.id, repository_id, "DELIVER",
                f"Pull request #{pr.pr_number} created: {pr.pr_url}. Delivery completed.",
            )
            return pr

        except DeliveryError as exc:
            await DeliveryService._fail(db, job, pr, repository_id, str(exc))
            raise HTTPException(status_code=409, detail=str(exc))
        except HTTPException as exc:
            await DeliveryService._fail(db, job, pr, repository_id, str(exc.detail))
            raise
        except Exception as exc:
            logger.exception(f"Unexpected delivery failure for job {job.id}")
            await DeliveryService._fail(db, job, pr, repository_id, f"Unexpected error: {exc}")
            raise HTTPException(status_code=500, detail=f"Delivery failed: {exc}")

    @staticmethod
    async def _fail(db: AsyncSession, job: MaintenanceJob, pr: PullRequest, repository_id: int, reason: str):
        try:
            pr.status = "delivery_failed"
            pr.failure_reason = reason
            job.status = "delivery_failed"
            await db.commit()
            await DeliveryService._log(db, job.id, repository_id, "ESCALATE", f"Delivery failed: {reason}", level="ERROR")
        except Exception:
            logger.exception("Failed to record delivery failure state.")

    # ------------------------------------------------------------------ PR content (evidence-based, no AI call)

    @staticmethod
    async def _build_pr_content(
        db: AsyncSession, issue: Optional[MaintenanceIssue], attempt: PatchAttempt,
        run: VerificationRun, checks: list, job: MaintenanceJob,
    ) -> Tuple[str, str]:
        plan = attempt.plan or {}
        summary = plan.get("summary") or (issue.title if issue else "Dependency maintenance patch")
        title = f"[TALOS] {summary}"[:200]

        package_name = issue.package_name if issue else None
        problem = (
            f"A vulnerable version of `{package_name}` was detected in this repository."
            if package_name else (issue.title if issue else "A maintenance issue was detected in this repository.")
        )

        actions = plan.get("actions") or []
        changes_md = "\n".join(f"- {a}" for a in actions) if actions else f"- {summary}"

        rows = []
        for c in checks:
            label = CHECK_LABELS.get(c.type, c.type)
            if c.type == "VULNERABILITY_RESCAN":
                if c.status == "PASSED":
                    result = "REMOVED"
                elif c.status == "FAILED":
                    result = "STILL PRESENT"
                else:
                    reason = (c.check_metadata or {}).get("reason", "unavailable")
                    result = f"SKIPPED ({reason})"
            elif c.status == "SKIPPED":
                reason = (c.check_metadata or {}).get("reason", "not applicable")
                result = f"SKIPPED ({reason})"
            else:
                result = c.status
            rows.append(f"| {label} | {result} |")
        table = "| Check | Result |\n|---|---|\n" + "\n".join(rows) if rows else "_No checks recorded._"

        risk = (job.risk_level or "unknown").upper()
        files_changed = len(attempt.files_modified or [])

        body = f"""## TALOS Maintenance Patch

### Problem

{problem}

### Changes

{changes_md}

### Verification

{table}

### Risk

{risk}

### Files Changed

{files_changed}

---

This patch was prepared and verified by TALOS (sandbox-isolated build/test/security checks, run #{run.id}).

**Human review is required before merge.**
"""
        return title, body

    # ------------------------------------------------------------------ lookups

    @staticmethod
    async def _get_repository(db: AsyncSession, user_id: int, repository_id: int) -> Repository:
        stmt = select(Repository).where(
            Repository.id == repository_id, Repository.user_id == user_id, Repository.connection_status != "disconnected",
        )
        result = await db.execute(stmt)
        repo = result.scalars().first()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found.")
        return repo

    @staticmethod
    async def _get_job(db: AsyncSession, repository_id: int, job_id: int) -> MaintenanceJob:
        stmt = select(MaintenanceJob).where(MaintenanceJob.id == job_id, MaintenanceJob.repository_id == repository_id)
        result = await db.execute(stmt)
        job = result.scalars().first()
        if not job:
            raise HTTPException(status_code=404, detail="Maintenance job not found.")
        return job

    @staticmethod
    async def _get_issue(db: AsyncSession, issue_id: Optional[int]) -> Optional[MaintenanceIssue]:
        if not issue_id:
            return None
        stmt = select(MaintenanceIssue).where(MaintenanceIssue.id == issue_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def _get_latest_ready_attempt(db: AsyncSession, job_id: int) -> Optional[PatchAttempt]:
        stmt = (
            select(PatchAttempt)
            .where(PatchAttempt.job_id == job_id, PatchAttempt.status == "ready")
            .order_by(desc(PatchAttempt.attempt_number))
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def _get_latest_verified_run(db: AsyncSession, patch_attempt_id: int) -> Optional[VerificationRun]:
        stmt = (
            select(VerificationRun)
            .where(VerificationRun.patch_attempt_id == patch_attempt_id, VerificationRun.status == "verified")
            .order_by(desc(VerificationRun.completed_at))
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def _get_checks(db: AsyncSession, run_id: int) -> list:
        stmt = select(VerificationCheck).where(VerificationCheck.verification_run_id == run_id).order_by(VerificationCheck.order_index)
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def _get_existing_pull_request(db: AsyncSession, job_id: int) -> Optional[PullRequest]:
        stmt = select(PullRequest).where(PullRequest.maintenance_job_id == job_id).order_by(desc(PullRequest.created_at))
        result = await db.execute(stmt)
        return result.scalars().first()

    # ------------------------------------------------------------------ response assembly

    @staticmethod
    def to_response_dict(pr: PullRequest) -> dict:
        return {
            "id": pr.id,
            "repository_id": pr.repository_id,
            "maintenance_job_id": pr.maintenance_job_id,
            "patch_attempt_id": pr.patch_attempt_id,
            "verification_run_id": pr.verification_run_id,
            "base_branch": pr.base_branch,
            "head_branch": pr.head_branch,
            "commit_sha": pr.commit_sha,
            "title": pr.title,
            "pr_number": pr.pr_number,
            "pr_url": pr.pr_url,
            "status": pr.status,
            "github_status": pr.github_status,
            "failure_reason": pr.failure_reason,
            "created_at": pr.created_at,
            "updated_at": pr.updated_at,
        }

    # ------------------------------------------------------------------ Phase 5 item 20: optional live status refresh

    @staticmethod
    async def refresh_status(db: AsyncSession, user_id: int, repository_id: int, pr_id: int, token: str) -> PullRequest:
        repo = await DeliveryService._get_repository(db, user_id, repository_id)
        stmt = select(PullRequest).where(PullRequest.id == pr_id, PullRequest.repository_id == repository_id)
        result = await db.execute(stmt)
        pr = result.scalars().first()
        if not pr:
            raise HTTPException(status_code=404, detail="Pull request not found.")
        if not pr.pr_number:
            return pr

        gh_pr = await GitHubService.get_pull_request(token, repo.owner, repo.name, pr.pr_number)
        pr.github_status = "merged" if gh_pr.get("merged") else gh_pr.get("state", pr.github_status)
        await db.commit()
        await db.refresh(pr)
        return pr
