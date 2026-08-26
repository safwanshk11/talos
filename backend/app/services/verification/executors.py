"""Phase 10: Verification Execution Adapter.

Where a verification check's commands actually run is now pluggable behind
`VerificationExecutor`. Everything else about Phase 4 — the plan TALOS
decides to run, the pass/fail/skipped semantics, the vulnerability re-scan,
the VERIFIED/VERIFICATION_FAILED verdict, the delivery-integrity gate — is
unchanged and lives in `verification_service.py`, executor-independent.

- `DockerVerificationExecutor` runs each check now, in-process, via the
  existing local docker-outside-of-docker sandbox (`SandboxService`) — the
  original Phase 4 behavior, untouched.
- `GitHubActionsVerificationExecutor` is for deployments with no Docker
  socket (e.g. Render): it pushes the patch branch, dispatches a
  `workflow_dispatch` run on a GitHub-hosted runner, and returns immediately.
  The run stays "running" until the runner reports back through the signed
  `/api/internal/verification/{id}/callback` endpoint.
"""
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.future import MaintenanceJob, MaintenanceIssue, PatchAttempt, VerificationRun, VerificationCheck
from app.models.repository import Repository
from app.services.git_workspace_service import GitWorkspaceService, GitWorkspaceError
from app.services.github_service import GitHubService
from app.services.verification.plan_builder import PlannedCheck, REQUIRED_CHECKS
from app.services.verification.sandbox_service import SandboxService

logger = logging.getLogger("talos.verification.executors")

TIMEOUTS = {
    "INSTALL": settings.VERIFICATION_TIMEOUT_INSTALL,
    "BUILD": settings.VERIFICATION_TIMEOUT_BUILD,
    "TEST": settings.VERIFICATION_TIMEOUT_TEST,
}


class ExecutionOutcome(str, Enum):
    COMPLETED = "completed"    # every check ran and was persisted — caller finalizes now
    DISPATCHED = "dispatched"  # async — a later callback finalizes the run


@dataclass
class VerificationContext:
    db: AsyncSession
    run: VerificationRun
    job: MaintenanceJob
    issue: Optional[MaintenanceIssue]
    attempt: PatchAttempt
    repo: Repository
    workspace_path: str
    workspace_subdir: str
    ecosystem: str
    # Only checks with a real command — `command is None` entries are already
    # persisted as SKIPPED by the caller before an executor ever sees the plan.
    plan: List[PlannedCheck]
    token: str


class VerificationExecutor:
    async def run_plan(self, ctx: VerificationContext) -> ExecutionOutcome:
        raise NotImplementedError


class DockerVerificationExecutor(VerificationExecutor):
    """The original Phase 4 path: runs every check now, in this process,
    inside a disposable no-secrets Docker container."""

    async def run_plan(self, ctx: VerificationContext) -> ExecutionOutcome:
        image = settings.VERIFICATION_SANDBOX_IMAGE_NPM if ctx.ecosystem == "npm" else settings.VERIFICATION_SANDBOX_IMAGE_PIP
        required_failed = False

        for order_index, planned in enumerate(ctx.plan, start=1):
            if required_failed:
                ctx.db.add(VerificationCheck(
                    verification_run_id=ctx.run.id, type=planned.type, command=planned.command,
                    status="SKIPPED", order_index=order_index,
                    check_metadata={"reason": "An earlier required check failed; remaining checks skipped."},
                ))
                await ctx.db.commit()
                continue

            started_at = datetime.now(timezone.utc)
            timeout = TIMEOUTS.get(planned.type, settings.VERIFICATION_TIMEOUT_DEFAULT)

            result = SandboxService.run(
                image=image,
                workspace_subdir=ctx.workspace_subdir,
                command=planned.command,
                timeout=timeout,
                memory=settings.VERIFICATION_MEMORY_LIMIT,
                cpus=settings.VERIFICATION_CPU_LIMIT,
                run_label=f"{ctx.run.id}-{planned.type.lower()}",
            )

            status = "TIMED_OUT" if result.timed_out else ("PASSED" if result.exit_code == 0 else "FAILED")
            check_metadata = None
            if planned.type == "SECURITY_AUDIT":
                from app.services.verification.verification_service import VerificationService
                status, check_metadata = VerificationService._interpret_npm_audit(result)

            stdout_excerpt, stderr_excerpt = result.excerpt(SandboxService.OUTPUT_LIMIT)
            ctx.db.add(VerificationCheck(
                verification_run_id=ctx.run.id, type=planned.type, command=planned.command,
                status=status, exit_code=result.exit_code, duration_ms=result.duration_ms,
                stdout_excerpt=stdout_excerpt, stderr_excerpt=stderr_excerpt,
                check_metadata=check_metadata, order_index=order_index,
                started_at=started_at, completed_at=datetime.now(timezone.utc),
            ))
            await ctx.db.commit()

            if status in ("FAILED", "TIMED_OUT") and planned.type in REQUIRED_CHECKS:
                required_failed = True

        return ExecutionOutcome.COMPLETED


class GitHubActionsVerificationExecutor(VerificationExecutor):
    """Pushes the patch branch and dispatches a workflow_dispatch run on
    GITHUB_ACTIONS_REPO — a GitHub-hosted runner has no dependency on the
    backend's own Docker socket, which Render (and similar free-tier hosts)
    don't expose. Nothing here decides pass/fail; that's still entirely
    `verification_service.py`'s job once the callback arrives."""

    async def run_plan(self, ctx: VerificationContext) -> ExecutionOutcome:
        if not ctx.token:
            raise RuntimeError("GitHub Actions verification requires a connected GitHub account to push the patch branch.")
        if not ctx.attempt.branch_name:
            raise RuntimeError("Patch attempt has no branch to push for remote verification.")

        clone_url_authed = ctx.repo.clone_url
        if ctx.token and "github.com" in ctx.repo.clone_url:
            clone_url_authed = ctx.repo.clone_url.replace("https://github.com/", f"https://x-access-token:{ctx.token}@github.com/")
        try:
            GitWorkspaceService.push_branch(ctx.workspace_path, clone_url_authed, ctx.attempt.branch_name, token=ctx.token)
        except GitWorkspaceError as exc:
            raise RuntimeError(f"Could not push patch branch for remote verification: {exc}") from exc

        # Pre-create PENDING rows so the UI shows real progress immediately,
        # not a blank tab, while the runner works.
        for order_index, planned in enumerate(ctx.plan, start=1):
            ctx.db.add(VerificationCheck(
                verification_run_id=ctx.run.id, type=planned.type, command=planned.command,
                status="PENDING", order_index=order_index,
            ))
        await ctx.db.commit()

        callback_url = f"{settings.TALOS_API_URL.rstrip('/')}/api/internal/verification/{ctx.run.id}/callback"
        plan_payload = [{"type": c.type, "command": c.command, "required": c.type in REQUIRED_CHECKS} for c in ctx.plan]

        image = settings.VERIFICATION_SANDBOX_IMAGE_NPM if ctx.ecosystem == "npm" else settings.VERIFICATION_SANDBOX_IMAGE_PIP

        await GitHubService.dispatch_workflow(
            token=ctx.token,
            owner=settings.GITHUB_ACTIONS_REPO.split("/")[0],
            repo=settings.GITHUB_ACTIONS_REPO.split("/")[1],
            workflow_file=settings.GITHUB_ACTIONS_WORKFLOW_FILE,
            ref=settings.GITHUB_ACTIONS_REF,
            inputs={
                "verification_run_id": str(ctx.run.id),
                "callback_url": callback_url,
                "target_repo": ctx.repo.full_name,
                "target_ref": ctx.attempt.branch_name,
                "runtime_image": image,
                "plan": json.dumps(plan_payload),
            },
        )

        ctx.run.executor = "github_actions"
        await ctx.db.commit()
        return ExecutionOutcome.DISPATCHED


def get_verification_executor() -> VerificationExecutor:
    if settings.VERIFICATION_EXECUTOR == "github_actions":
        return GitHubActionsVerificationExecutor()
    return DockerVerificationExecutor()
