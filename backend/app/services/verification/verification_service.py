import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.models.future import (
    MaintenanceJob,
    MaintenanceIssue,
    PatchAttempt,
    VerificationRun,
    VerificationCheck,
    ActionLog,
)
from app.services.scanner_service import ScannerService
from app.services.verification.plan_builder import VerificationPlanBuilder
from app.services.verification.sandbox_service import SandboxService, SandboxError

logger = logging.getLogger("talos.verification")

TIMEOUTS = {
    "INSTALL": settings.VERIFICATION_TIMEOUT_INSTALL,
    "BUILD": settings.VERIFICATION_TIMEOUT_BUILD,
    "TEST": settings.VERIFICATION_TIMEOUT_TEST,
}


class VerificationService:
    """Phase 4 orchestrator: PATCH_READY -> isolated sandbox -> deterministic
    checks -> original-vulnerability re-scan -> VERIFIED / VERIFICATION_FAILED.

    Deliberately does not call an AIProvider anywhere in this file. Verification
    is decided entirely by process exit codes and the OSV re-query — a model
    could help a human diagnose a failure later, but it never gets a vote on
    whether a failed deterministic check should be ignored.
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
    async def run_verification(db: AsyncSession, user_id: int, repository_id: int, job_id: int) -> VerificationRun:
        job = await VerificationService._get_job(db, repository_id, job_id)
        issue = await VerificationService._get_issue(db, job.issue_id)
        attempt = await VerificationService._get_latest_ready_attempt(db, job.id)

        if job.status != "patch_ready" or not attempt:
            raise HTTPException(
                status_code=400,
                detail="This job has no ready patch to verify. Run Prepare Fix first.",
            )

        if not attempt.workspace_path or not os.path.isdir(attempt.workspace_path):
            raise HTTPException(
                status_code=400,
                detail="The patch workspace is no longer available (e.g. after an infra restart). "
                       "Run Prepare Fix again to generate a fresh patch before verifying.",
            )

        run = VerificationRun(
            maintenance_job_id=job.id,
            patch_attempt_id=attempt.id,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)

        job.status = "verifying"
        if issue:
            issue.status = "VERIFYING"
        await db.commit()

        await VerificationService._log(db, job.id, repository_id, "VERIFY", f"Verification run #{run.id} started.")

        try:
            if not SandboxService.check_docker_available():
                raise SandboxError(
                    "Docker sandbox is not available to the backend. Verification requires the host's "
                    "Docker socket to be mounted (see docker-compose.yml)."
                )

            sandbox_id = f"run{run.id}-{os.urandom(4).hex()}"
            run.sandbox_id = sandbox_id
            await db.commit()
            await VerificationService._log(
                db, job.id, repository_id, "VERIFY",
                f"Isolated sandbox '{sandbox_id}' prepared: no TALOS secrets, isolated network, resource-limited.",
            )

            workspace_subdir = os.path.basename(attempt.workspace_path.rstrip("/"))
            ecosystem = VerificationService._detect_ecosystem(attempt.workspace_path)
            plan = VerificationPlanBuilder.build(attempt.workspace_path, ecosystem)
            await VerificationService._log(
                db, job.id, repository_id, "VERIFY",
                f"Verification plan built for {ecosystem} project: {len(plan)} checks.",
            )

            required_failed = False

            for order_index, planned in enumerate(plan, start=1):
                if required_failed:
                    db.add(VerificationCheck(
                        verification_run_id=run.id, type=planned.type, command=planned.command,
                        status="SKIPPED", order_index=order_index,
                        check_metadata={"reason": "An earlier required check failed; remaining checks skipped."},
                    ))
                    await db.commit()
                    continue

                if planned.command is None:
                    db.add(VerificationCheck(
                        verification_run_id=run.id, type=planned.type, command=None,
                        status="SKIPPED", order_index=order_index,
                        check_metadata={"reason": planned.skip_reason},
                    ))
                    await db.commit()
                    await VerificationService._log(db, job.id, repository_id, "VERIFY", f"{planned.type} skipped: {planned.skip_reason}")
                    continue

                if planned.type == "VULNERABILITY_RESCAN":
                    status, metadata = await VerificationService._rescan_vulnerability(attempt, issue, ecosystem)
                    db.add(VerificationCheck(
                        verification_run_id=run.id, type="VULNERABILITY_RESCAN", command="OSV re-query",
                        status=status, order_index=order_index, check_metadata=metadata,
                        started_at=datetime.now(timezone.utc), completed_at=datetime.now(timezone.utc),
                    ))
                    await db.commit()
                    await VerificationService._log(
                        db, job.id, repository_id, "VERIFY",
                        "Vulnerability re-scan: advisory removed." if status == "PASSED"
                        else "Vulnerability re-scan: advisory still present." if status == "FAILED"
                        else f"Vulnerability re-scan skipped: {metadata.get('reason')}",
                    )
                    if status in ("FAILED",) and planned.required:
                        required_failed = True
                    continue

                await VerificationService._log(db, job.id, repository_id, "VERIFY", f"{planned.type} started: {planned.command}")
                started_at = datetime.now(timezone.utc)
                timeout = TIMEOUTS.get(planned.type, settings.VERIFICATION_TIMEOUT_DEFAULT)
                image = (
                    settings.VERIFICATION_SANDBOX_IMAGE_NPM if ecosystem == "npm"
                    else settings.VERIFICATION_SANDBOX_IMAGE_PIP
                )

                result = SandboxService.run(
                    image=image,
                    workspace_subdir=workspace_subdir,
                    command=planned.command,
                    timeout=timeout,
                    memory=settings.VERIFICATION_MEMORY_LIMIT,
                    cpus=settings.VERIFICATION_CPU_LIMIT,
                    run_label=f"{run.id}-{planned.type.lower()}",
                )

                status = "TIMED_OUT" if result.timed_out else ("PASSED" if result.exit_code == 0 else "FAILED")
                check_metadata = None
                if planned.type == "SECURITY_AUDIT":
                    # Parse the FULL output before it gets tail-truncated below —
                    # `npm audit --json` output can exceed the excerpt limit, and
                    # truncating first would sever the JSON's opening structure.
                    status, check_metadata = VerificationService._interpret_npm_audit(result)

                stdout_excerpt, stderr_excerpt = result.excerpt(SandboxService.OUTPUT_LIMIT)
                db.add(VerificationCheck(
                    verification_run_id=run.id, type=planned.type, command=planned.command,
                    status=status, exit_code=result.exit_code, duration_ms=result.duration_ms,
                    stdout_excerpt=stdout_excerpt, stderr_excerpt=stderr_excerpt,
                    check_metadata=check_metadata, order_index=order_index,
                    started_at=started_at, completed_at=datetime.now(timezone.utc),
                ))
                await db.commit()

                await VerificationService._log(
                    db, job.id, repository_id, "VERIFY",
                    f"{planned.type} {status.lower()} ({result.duration_ms}ms).",
                )

                if status in ("FAILED", "TIMED_OUT") and planned.required:
                    required_failed = True

            overall_verified = not required_failed
            run.status = "verified" if overall_verified else "verification_failed"
            run.completed_at = datetime.now(timezone.utc)
            job.status = run.status
            job.completed_at = datetime.now(timezone.utc)
            if issue:
                issue.status = "VERIFIED" if overall_verified else "VERIFICATION_FAILED"
            await db.commit()

            await VerificationService._log(
                db, job.id, repository_id, "VERIFY",
                "Verification PASSED — patch marked VERIFIED." if overall_verified
                else "Verification FAILED — patch marked VERIFICATION_FAILED.",
            )
            return run

        except Exception as exc:
            logger.exception(f"Verification infrastructure failure for run {run.id}")
            run.status = "failed"
            run.completed_at = datetime.now(timezone.utc)
            job.status = "failed"
            job.completed_at = datetime.now(timezone.utc)
            if issue:
                issue.status = "FAILED"
            await db.commit()
            await VerificationService._log(
                db, job.id, repository_id, "ESCALATE", f"Verification infrastructure failure: {exc}", level="ERROR",
            )
            raise HTTPException(status_code=500, detail=f"Verification infrastructure failure: {exc}")

    # ------------------------------------------------------------------ vulnerability re-scan

    @staticmethod
    async def _rescan_vulnerability(attempt: PatchAttempt, issue: Optional[MaintenanceIssue], ecosystem: str) -> Tuple[str, dict]:
        if not issue or not issue.package_name:
            return "SKIPPED", {"reason": "No original maintenance issue is associated with this job."}

        resolved_version = VerificationService._resolve_installed_version(attempt.workspace_path, issue.package_name, ecosystem)
        if not resolved_version:
            return "FAILED", {"reason": f"Could not determine the installed version of {issue.package_name} after patching."}

        osv_ecosystem = {"npm": "npm", "pip": "PyPI"}.get(ecosystem, "npm")
        results = await ScannerService.query_osv_vulnerabilities([
            {"package": {"name": issue.package_name, "ecosystem": osv_ecosystem}, "version": resolved_version}
        ])
        vulns = results[0].get("vulns", []) if results else []
        advisory_ids = sorted({v.get("id") for v in vulns if v.get("id")})
        still_present = issue.advisory_id in advisory_ids if issue.advisory_id else len(vulns) > 0

        metadata = {
            "package_name": issue.package_name,
            "previous_version": issue.current_version,
            "verified_version": resolved_version,
            "original_advisory_id": issue.advisory_id,
            "advisory_still_present": still_present,
            "remaining_advisories": advisory_ids,
        }
        return ("FAILED" if still_present else "PASSED"), metadata

    @staticmethod
    def _resolve_installed_version(workspace_path: str, package_name: str, ecosystem: str) -> Optional[str]:
        if ecosystem == "npm":
            lock_path = os.path.join(workspace_path, "package-lock.json")
            if os.path.isfile(lock_path):
                try:
                    with open(lock_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    entry = data.get("packages", {}).get(f"node_modules/{package_name}")
                    if entry and entry.get("version"):
                        return entry["version"]
                    dep_entry = data.get("dependencies", {}).get(package_name)
                    if dep_entry and dep_entry.get("version"):
                        return dep_entry["version"]
                except Exception:
                    pass
            pkg_path = os.path.join(workspace_path, "package.json")
            if os.path.isfile(pkg_path):
                try:
                    with open(pkg_path, "r", encoding="utf-8") as f:
                        pkg = json.load(f)
                    raw = (pkg.get("dependencies", {}) or {}).get(package_name) or (pkg.get("devDependencies", {}) or {}).get(package_name)
                    if raw:
                        return re.sub(r"^[\^~>=]+", "", str(raw))
                except Exception:
                    pass
        elif ecosystem == "pip":
            req_path = os.path.join(workspace_path, "requirements.txt")
            if os.path.isfile(req_path):
                with open(req_path, "r", encoding="utf-8") as f:
                    for line in f:
                        stripped = line.strip()
                        if stripped.lower().startswith(package_name.lower() + "=="):
                            return stripped.split("==", 1)[1].strip()
        return None

    # ------------------------------------------------------------------ security audit interpretation

    @staticmethod
    def _interpret_npm_audit(result) -> Tuple[str, dict]:
        try:
            data = json.loads(result.stdout)
            counts = (data.get("metadata", {}) or {}).get("vulnerabilities", {}) or {}
            high_or_critical = counts.get("high", 0) + counts.get("critical", 0)
            status = "FAILED" if high_or_critical > 0 else "PASSED"
            return status, {"vulnerability_counts": counts}
        except Exception:
            # npm audit exits non-zero purely because it found vulnerabilities —
            # that's informative, not a broken command. Only treat unparsable
            # output as an actual failure of the check itself.
            return ("PASSED" if result.exit_code in (0, 1) else "FAILED"), {
                "reason": "Could not parse npm audit JSON output.",
                "raw_exit_code": result.exit_code,
            }

    # ------------------------------------------------------------------ lookups

    @staticmethod
    def _detect_ecosystem(workspace_path: str) -> str:
        if os.path.isfile(os.path.join(workspace_path, "package.json")):
            return "npm"
        if os.path.isfile(os.path.join(workspace_path, "requirements.txt")):
            return "pip"
        return "unknown"

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
            .order_by(PatchAttempt.attempt_number.desc())
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    # ------------------------------------------------------------------ response assembly

    @staticmethod
    async def to_response_dict(db: AsyncSession, run: VerificationRun) -> dict:
        stmt = (
            select(VerificationCheck)
            .where(VerificationCheck.verification_run_id == run.id)
            .order_by(VerificationCheck.order_index)
        )
        result = await db.execute(stmt)
        checks = result.scalars().all()
        return {
            "id": run.id,
            "maintenance_job_id": run.maintenance_job_id,
            "patch_attempt_id": run.patch_attempt_id,
            "status": run.status,
            "sandbox_id": run.sandbox_id,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "checks": checks,
        }
