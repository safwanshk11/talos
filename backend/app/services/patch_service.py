import json
import logging
import os
import re
import subprocess
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from fastapi import HTTPException

from app.models.repository import Repository
from app.models.dependency import Dependency
from app.models.readiness import RepositoryReadiness
from app.models.future import MaintenanceIssue, MaintenanceJob, PatchAttempt, ActionLog
from app.services.context_service import ContextEngine
from app.services.git_workspace_service import GitWorkspaceService, GitWorkspaceError
from app.services.dependency_updater_service import DependencyUpdaterService, DependencyUpdateError
from app.services.scanner_service import ScannerService
from app.services.patch_safety import (
    validate_and_resolve,
    enforce_content_limit,
    enforce_file_count_limit,
    PatchSafetyError,
)
from app.services.ai.factory import get_ai_provider
from app.services.ai.base import AIProviderError
from app.services.ai.schemas import RiskLevel, ProblemAnalysis, MaintenancePlan
from app.services.decision_service import (
    DecisionService,
    PolicyService,
    PatchInput,
    VerificationCapability,
    classify_dependency_bump,
    UPDATE_TYPE_SECURITY_PATCH,
    DECISION_AUTO_EXECUTE,
    DECISION_APPROVAL_REQUIRED,
    DECISION_ESCALATE,
    DECISION_IGNORE,
    DECISION_BLOCKED_BY_CONFLICT,
)

logger = logging.getLogger("talos.patch")


class PatchServiceError(Exception):
    pass


class PatchService:
    """Orchestrates the Phase 3 workflow:
    Select Issue -> Gather Context -> Analyze -> Plan -> Assess Risk ->
    Isolated Workspace -> TALOS Branch -> Generate Patch -> Apply -> Diff -> PATCH_READY

    The original/default branch is never touched: TALOS only ever operates inside a
    disposable local clone and never pushes anywhere.
    """

    BRANCH_PREFIX = "talos/fix"

    # ------------------------------------------------------------------ ledger

    @staticmethod
    async def _log(db: AsyncSession, job_id: int, repository_id: int, step: str, message: str, level: str = "INFO"):
        entry = ActionLog(
            repository_id=repository_id,
            job_id=job_id,
            step=step,
            message=message,
            level=level,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(entry)
        await db.commit()

    # ------------------------------------------------------------------ entrypoint

    @staticmethod
    async def prepare_fix(db: AsyncSession, user_id: int, repository_id: int, issue_id: int, token: str, trigger: str = "manual") -> MaintenanceJob:
        """`trigger` (Phase 7) records provenance only — manual/scheduled_scan/
        github_push — and never changes what the Decision Engine permits."""
        repo = await PatchService._get_repository(db, user_id, repository_id)
        issue = await PatchService._get_issue(db, repository_id, issue_id)

        attempt_number = await PatchService._next_attempt_number(db, issue_id)

        job = MaintenanceJob(repository_id=repository_id, issue_id=issue_id, status="analyzing", trigger=trigger)
        db.add(job)
        await db.commit()
        await db.refresh(job)

        # -------------------------------------------------- Phase 6.5: pre-flight decision
        # Hard safety rules (repository paused, conflicting job, duplicate open PR) are
        # checked before any clone/AI cost is spent — deterministic, no network call.
        policy = await PolicyService.get_or_create(db, repository_id)
        preflight = await DecisionService.decide(db, repo, issue, job, policy, patch=None, verification=None)
        if preflight.decision in (DECISION_IGNORE, DECISION_BLOCKED_BY_CONFLICT):
            job.status = "ignored" if preflight.decision == DECISION_IGNORE else "blocked_conflict"
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return job

        issue.status = "ANALYZING"
        await db.commit()

        workspace_path: Optional[str] = None
        keep_workspace = False

        try:
            await PatchService._log(
                db, job.id, repository_id, "UNDERSTAND",
                f"Maintenance job #{job.id} started for issue #{issue.id} ({issue.package_name or issue.title}), attempt {attempt_number}."
            )

            # -------------------------------------------------- gather repository context
            workspace_path = GitWorkspaceService.create_workspace(job.id)
            clone_url_authed = repo.clone_url
            if token and "github.com" in repo.clone_url:
                clone_url_authed = repo.clone_url.replace(
                    "https://github.com/", f"https://x-access-token:{token}@github.com/"
                )

            try:
                GitWorkspaceService.clone_repository(clone_url_authed, repo.default_branch, workspace_path)
            except GitWorkspaceError as exc:
                raise PatchServiceError(f"Workspace creation failed: {exc}") from exc

            GitWorkspaceService.configure_identity(workspace_path)
            base_sha = GitWorkspaceService.get_head_sha(workspace_path)
            await PatchService._log(db, job.id, repository_id, "UNDERSTAND", "Isolated repository workspace created from default branch.")

            readiness = await PatchService._get_readiness(db, repository_id)
            context = ContextEngine.build_context(issue, workspace_path, readiness=readiness)
            await PatchService._log(
                db, job.id, repository_id, "UNDERSTAND",
                f"{len(context.sections)} context sections selected ({context.total_chars} chars) from Phase 2 findings."
            )

            try:
                provider = get_ai_provider()
            except AIProviderError as exc:
                raise PatchServiceError(f"AI provider unavailable: {exc}") from exc

            # -------------------------------------------------- analyze
            prompt_context = context.to_prompt()
            try:
                analysis = await provider.analyze_problem(prompt_context)
            except AIProviderError as exc:
                raise PatchServiceError(f"AI analysis failed: {exc}") from exc
            await PatchService._log(db, job.id, repository_id, "UNDERSTAND", f"AI analysis completed via {provider.name}:{provider.model}.")

            if analysis.escalation_required:
                await PatchService._escalate(
                    db, job, issue, attempt_number, provider, analysis, None,
                    reason=analysis.escalation_reason or "AI reported missing information required for a safe analysis.",
                )
                return job

            # -------------------------------------------------- plan
            job.status = "planning"
            issue.status = "PLANNING"
            await db.commit()

            try:
                plan = await provider.generate_plan(prompt_context, analysis)
            except AIProviderError as exc:
                raise PatchServiceError(f"Plan generation failed: {exc}") from exc

            await PatchService._log(db, job.id, repository_id, "PLAN", f"Maintenance plan created: {plan.summary}")

            job.risk_level = plan.risk.value.lower()
            job.risk_reason = plan.risk_reason
            await db.commit()
            await PatchService._log(db, job.id, repository_id, "PLAN", f"Risk classified {plan.risk.value}: {plan.risk_reason}")

            if plan.escalate or plan.risk == RiskLevel.HIGH:
                reason = plan.escalation_reason or (
                    f"Risk classified {plan.risk.value}; TALOS does not autonomously patch HIGH risk changes."
                )
                await PatchService._escalate(db, job, issue, attempt_number, provider, analysis, plan, reason=reason)
                return job

            # -------------------------------------------------- Phase 6.5: full decision
            # Now that risk and the concrete file set are known, evaluate the real
            # decision: AUTO_EXECUTE / PREPARE_ONLY / APPROVAL_REQUIRED / ESCALATE / IGNORE.
            dependency = await PatchService._get_dependency(db, repository_id, issue.package_name)
            target_version = plan.target_version if plan.target_version and plan.target_version != "N/A" else issue.recommended_version
            if issue.category == "vulnerability":
                update_type = UPDATE_TYPE_SECURITY_PATCH
            else:
                update_type = classify_dependency_bump(issue.current_version, target_version)

            patch_input = PatchInput(risk=plan.risk.value, update_type=update_type, files=plan.files_to_modify)
            verification_cap = VerificationCapability(
                build_available=bool(readiness.build_script_found) if readiness else False,
                tests_available=bool(readiness.test_script_found) if readiness else False,
                security_audit_available=(dependency.ecosystem == "npm") if dependency else False,
                readiness_level=readiness.score_level if readiness else "LOW",
            )
            full_decision = await DecisionService.decide(db, repo, issue, job, policy, patch_input, verification_cap)

            if full_decision.decision == DECISION_ESCALATE:
                await PatchService._escalate(db, job, issue, attempt_number, provider, analysis, plan, reason=full_decision.reason)
                return job

            if full_decision.decision == DECISION_APPROVAL_REQUIRED:
                # Persist the exact analysis/plan TALOS already produced so approval
                # resumes this same artifact rather than asking the model again.
                pending = PatchAttempt(
                    job_id=job.id, branch_name="", base_sha=base_sha, attempt_number=attempt_number,
                    status="awaiting_approval", ai_provider=provider.name, ai_model=provider.model,
                    analysis=analysis.model_dump(mode="json"), plan=plan.model_dump(mode="json"),
                    workspace_path=workspace_path, started_at=job.created_at,
                )
                db.add(pending)
                job.status = "waiting_for_approval"
                issue.status = "APPROVAL_REQUIRED"
                await db.commit()
                keep_workspace = True
                await PatchService._log(db, job.id, repository_id, "DECIDE", "Autonomous execution paused: developer approval required before continuing.")
                return job

            if full_decision.decision == DECISION_IGNORE:
                job.status = "ignored"
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()
                return job

            job.status = "planned"
            issue.status = "PLANNED"
            await db.commit()

            job = await PatchService._finalize_patch(
                db, job, issue, repo, provider, analysis, plan,
                workspace_path, base_sha, attempt_number, dependency, token,
                auto_chain=(full_decision.decision == DECISION_AUTO_EXECUTE),
            )
            keep_workspace = True
            return job

        except PatchServiceError as exc:
            await PatchService._fail(db, job, issue, repository_id, attempt_number, str(exc))
            raise
        except (DependencyUpdateError, PatchSafetyError, GitWorkspaceError) as exc:
            await PatchService._fail(db, job, issue, repository_id, attempt_number, str(exc))
            raise
        except subprocess.TimeoutExpired as exc:
            await PatchService._fail(db, job, issue, repository_id, attempt_number, f"Operation timed out: {exc}")
            raise
        except Exception as exc:
            logger.exception(f"Unexpected patch service failure for job {job.id}")
            await PatchService._fail(db, job, issue, repository_id, attempt_number, f"Unexpected error: {exc}")
            raise
        finally:
            if workspace_path and not keep_workspace:
                GitWorkspaceService.cleanup(workspace_path)

    # ------------------------------------------------------------------ decision-gated continuation

    @staticmethod
    async def _finalize_patch(
        db: AsyncSession, job: MaintenanceJob, issue: MaintenanceIssue, repo: Repository,
        provider, analysis: ProblemAnalysis, plan: MaintenancePlan,
        workspace_path: str, base_sha: str, attempt_number: int,
        dependency: Optional[Dependency], token: str, auto_chain: bool,
    ) -> MaintenanceJob:
        """The branch/patch/commit/diff half of the pipeline — shared by a normal
        AUTO_EXECUTE/PREPARE_ONLY run and by resume_after_approval, which reuses
        the exact analysis/plan already produced rather than asking the model
        again. When auto_chain is True (Phase 6.5 AUTO_EXECUTE, or an approved
        job), continues straight through Phase 4 verification and, if genuinely
        verified, Phase 5 delivery — all still gated by DeliveryService's own
        hard server-side VERIFIED check."""
        repository_id = repo.id

        job.status = "sandboxing"
        await db.commit()

        slug = re.sub(r"[^a-z0-9]+", "-", (issue.package_name or issue.title or "issue").lower()).strip("-")[:30]
        branch_name = f"{PatchService.BRANCH_PREFIX}-{issue.id}-{slug}"
        try:
            GitWorkspaceService.create_branch(workspace_path, branch_name)
        except GitWorkspaceError as exc:
            raise PatchServiceError(f"Branch creation failed: {exc}") from exc
        await PatchService._log(db, job.id, repository_id, "PATCH", f"TALOS branch '{branch_name}' created; default branch untouched.")

        job.status = "patching"
        issue.status = "PATCHING"
        await db.commit()

        files_modified: List[str] = []
        target_version = plan.target_version if plan.target_version and plan.target_version != "N/A" else issue.recommended_version

        if dependency and target_version:
            await PatchService._apply_dependency_update(workspace_path, dependency, target_version)
            files_modified.extend(PatchService._changed_files(workspace_path))
            await PatchService._log(
                db, job.id, repository_id, "PATCH",
                f"Dependency {dependency.name} deterministically updated to {target_version} via package manager."
            )

        code_files = [
            f for f in plan.files_to_modify
            if f not in files_modified and not f.endswith((".lock", "-lock.json", "-lock.yaml"))
            and f not in ("package.json", "requirements.txt", "pyproject.toml")
        ]
        if plan.requires_code_changes and code_files:
            # Rebuilding the context is deterministic (issue + workspace + readiness) —
            # the plan itself (the actual artifact) is never regenerated, only its
            # prompt framing is recomputed so generate_patch has it to work from.
            readiness = await PatchService._get_readiness(db, repository_id)
            context = ContextEngine.build_context(issue, workspace_path, readiness=readiness)
            prompt_context = context.to_prompt()
            try:
                patch_result = await provider.generate_patch(prompt_context, plan)
            except AIProviderError as exc:
                raise PatchServiceError(f"Patch generation failed: {exc}") from exc

            enforce_file_count_limit(len(patch_result.edits))
            applied = 0
            for edit in patch_result.edits:
                if edit.path not in plan.files_to_modify:
                    logger.warning(f"Ignoring unauthorized file edit outside plan.files_to_modify: {edit.path}")
                    continue
                enforce_content_limit(edit.new_content, edit.path)
                full_path = validate_and_resolve(workspace_path, edit.path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(edit.new_content)
                files_modified.append(edit.path)
                applied += 1
            await PatchService._log(db, job.id, repository_id, "PATCH", f"{applied} source file(s) modified per plan.")

        commit_message = f"talos: {plan.summary}"[:200]
        try:
            commit_sha = GitWorkspaceService.commit_all(workspace_path, commit_message)
        except GitWorkspaceError as exc:
            raise PatchServiceError(f"Commit failed: {exc}") from exc

        if not commit_sha:
            if dependency:
                still_vulnerable = await PatchService._is_still_vulnerable(workspace_path, issue, dependency.ecosystem)
                if still_vulnerable is False:
                    await PatchService._resolve_already_fixed(db, job, issue, repository_id)
                    return job
            raise PatchServiceError("No file changes were produced; nothing to patch.")

        diff_text = GitWorkspaceService.diff_against_sha(workspace_path, base_sha)
        files_modified = sorted(set(files_modified))
        await PatchService._log(
            db, job.id, repository_id, "PATCH",
            f"Patch created on '{branch_name}': {len(files_modified)} file(s) changed."
        )

        attempt = PatchAttempt(
            job_id=job.id, branch_name=branch_name, base_sha=base_sha, commit_sha=commit_sha,
            patch_diff=diff_text, attempt_number=attempt_number, status="ready",
            ai_provider=provider.name, ai_model=provider.model,
            analysis=analysis.model_dump(mode="json"), plan=plan.model_dump(mode="json"),
            files_modified=files_modified, workspace_path=workspace_path,
            started_at=job.created_at, completed_at=datetime.now(timezone.utc),
        )
        db.add(attempt)

        job.status = "patch_ready"
        job.completed_at = datetime.now(timezone.utc)
        issue.status = "PATCH_READY"
        await db.commit()
        await PatchService._log(
            db, job.id, repository_id, "VERIFY",
            "Patch prepared. Awaiting verification (Phase 4). Original branch untouched."
        )

        if auto_chain:
            await PatchService._auto_chain(db, job, repo, token)
            await db.refresh(job)

        return job

    @staticmethod
    async def _auto_chain(db: AsyncSession, job: MaintenanceJob, repo: Repository, token: str):
        """AUTO_EXECUTE (or an approved job) continues straight through Phase 4
        verification and, if genuinely verified, Phase 5 delivery — all in the
        same request, matching this codebase's existing synchronous architecture.
        Any failure here just leaves the job in whatever real state verification/
        delivery produced; nothing is faked, and TALOS still never merges."""
        from app.services.verification.verification_service import VerificationService
        from app.services.delivery_service import DeliveryService

        try:
            await PatchService._log(db, job.id, repo.id, "VERIFY", "Autonomous execution: proceeding directly to verification (policy permits AUTO_EXECUTE).")
            await VerificationService.run_verification(db, repo.user_id, repo.id, job.id)
        except Exception as exc:
            logger.warning(f"Auto-chain verification did not complete for job {job.id}: {exc}")
            return

        await db.refresh(job)
        if job.status != "verified":
            return

        try:
            await PatchService._log(db, job.id, repo.id, "DELIVER", "Autonomous execution: verification passed, proceeding directly to delivery.")
            await DeliveryService.deliver(db, repo.user_id, repo.id, job.id, token)
        except Exception as exc:
            logger.warning(f"Auto-chain delivery did not complete for job {job.id}: {exc}")

    @staticmethod
    async def resume_after_approval(db: AsyncSession, user_id: int, repository_id: int, issue_id: int, job_id: int, token: str) -> MaintenanceJob:
        """Backend enforcement for Phase 6.5 approval (section 25): only a job
        genuinely in waiting_for_approval, for a repository this user owns, can
        be resumed — and it resumes the exact analysis/plan TALOS already
        produced rather than contacting the AI provider again."""
        repo = await PatchService._get_repository(db, user_id, repository_id)
        issue = await PatchService._get_issue(db, repository_id, issue_id)
        job = await PatchService._get_job(db, repository_id, job_id)

        if job.status != "waiting_for_approval":
            raise HTTPException(status_code=400, detail="This job is not awaiting approval.")

        stmt = (
            select(PatchAttempt)
            .where(PatchAttempt.job_id == job.id, PatchAttempt.status == "awaiting_approval")
            .order_by(desc(PatchAttempt.attempt_number))
        )
        result = await db.execute(stmt)
        pending = result.scalars().first()
        if not pending or not pending.workspace_path or not os.path.isdir(pending.workspace_path):
            raise HTTPException(status_code=400, detail="The pending patch workspace is no longer available; run Prepare Fix again.")

        job.approved_at = datetime.now(timezone.utc)
        await db.commit()
        await PatchService._log(db, job.id, repository_id, "DECIDE", "Developer approved autonomous continuation.")

        analysis = ProblemAnalysis(**pending.analysis)
        plan = MaintenancePlan(**pending.plan)
        try:
            provider = get_ai_provider()
        except AIProviderError as exc:
            raise PatchServiceError(f"AI provider unavailable: {exc}") from exc

        dependency = await PatchService._get_dependency(db, repository_id, issue.package_name)

        job.status = "planned"
        issue.status = "PLANNED"
        await db.commit()

        try:
            job = await PatchService._finalize_patch(
                db, job, issue, repo, provider, analysis, plan,
                pending.workspace_path, pending.base_sha, pending.attempt_number, dependency, token,
                auto_chain=True,
            )
            return job
        except (PatchServiceError, DependencyUpdateError, PatchSafetyError, GitWorkspaceError) as exc:
            await PatchService._fail(db, job, issue, repository_id, pending.attempt_number, str(exc))
            GitWorkspaceService.cleanup(pending.workspace_path)
            raise
        except Exception as exc:
            logger.exception(f"Unexpected failure resuming approved job {job.id}")
            await PatchService._fail(db, job, issue, repository_id, pending.attempt_number, f"Unexpected error: {exc}")
            GitWorkspaceService.cleanup(pending.workspace_path)
            raise

    @staticmethod
    async def reject(db: AsyncSession, user_id: int, repository_id: int, issue_id: int, job_id: int, reason: Optional[str]) -> MaintenanceJob:
        repo = await PatchService._get_repository(db, user_id, repository_id)
        issue = await PatchService._get_issue(db, repository_id, issue_id)
        job = await PatchService._get_job(db, repository_id, job_id)

        if job.status != "waiting_for_approval":
            raise HTTPException(status_code=400, detail="This job is not awaiting approval.")

        stmt = select(PatchAttempt).where(PatchAttempt.job_id == job.id, PatchAttempt.status == "awaiting_approval")
        result = await db.execute(stmt)
        pending = result.scalars().first()
        if pending and pending.workspace_path:
            GitWorkspaceService.cleanup(pending.workspace_path)

        job.status = "rejected"
        job.rejected_at = datetime.now(timezone.utc)
        job.rejection_reason = reason
        job.completed_at = datetime.now(timezone.utc)
        issue.status = "REJECTED_BY_USER"
        await db.commit()
        await PatchService._log(
            db, job.id, repository_id, "DECIDE",
            f"Developer rejected autonomous action.{f' Reason: {reason}' if reason else ''}",
            level="WARNING",
        )
        return job

    # ------------------------------------------------------------------ helpers

    @staticmethod
    async def _apply_dependency_update(workspace_path: str, dependency: Dependency, target_version: str):
        if dependency.ecosystem == "npm":
            DependencyUpdaterService.update_npm_dependency(
                workspace_path, dependency.name, target_version, dependency.dep_type
            )
        elif dependency.ecosystem == "pip":
            DependencyUpdaterService.update_pip_requirement(workspace_path, dependency.name, target_version)
        else:
            raise PatchServiceError(f"Unsupported ecosystem for deterministic update: {dependency.ecosystem}")

    @staticmethod
    async def _is_still_vulnerable(workspace_path: str, issue: MaintenanceIssue, ecosystem: str) -> Optional[bool]:
        """Real OSV re-query against the version actually installed in the freshly
        cloned workspace. Returns None (unknown) rather than guessing if the
        version can't be determined or the issue has no advisory to check."""
        if not issue.package_name or not issue.advisory_id:
            return None
        resolved_version = PatchService._resolve_installed_version(workspace_path, issue.package_name, ecosystem)
        if not resolved_version:
            return None
        osv_ecosystem = {"npm": "npm", "pip": "PyPI"}.get(ecosystem, "npm")
        results = await ScannerService.query_osv_vulnerabilities([
            {"package": {"name": issue.package_name, "ecosystem": osv_ecosystem}, "version": resolved_version}
        ])
        vulns = results[0].get("vulns", []) if results else []
        advisory_ids = {v.get("id") for v in vulns if v.get("id")}
        return issue.advisory_id in advisory_ids

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

    @staticmethod
    async def _resolve_already_fixed(db, job: MaintenanceJob, issue: MaintenanceIssue, repository_id: int):
        """The vulnerability this issue was opened for is confirmed gone from the
        repository's current default branch (verified via a real OSV re-query, not
        assumed) — most likely fixed directly on the default branch since detection.
        No patch was needed, so none was fabricated; the issue is closed with the
        same RESOLVED status Phase 2's scan dedup already uses for this exact case."""
        job.status = "resolved"
        job.completed_at = datetime.now(timezone.utc)
        issue.status = "RESOLVED"
        issue.resolved_at = datetime.now(timezone.utc)
        await db.commit()
        await PatchService._log(
            db, job.id, repository_id, "PATCH",
            f"No patch needed: {issue.package_name} on the default branch already resolves "
            f"advisory {issue.advisory_id} (confirmed via OSV re-query). Issue marked RESOLVED.",
        )

    @staticmethod
    def _changed_files(workspace_path: str) -> List[str]:
        proc = subprocess.run(["git", "status", "--porcelain"], cwd=workspace_path, capture_output=True, text=True)
        changed = []
        for line in proc.stdout.splitlines():
            path = line[3:].strip()
            if path:
                changed.append(path)
        return changed

    @staticmethod
    async def _escalate(db, job, issue, attempt_number, provider, analysis, plan, reason: str):
        job.status = "escalated"
        job.completed_at = datetime.now(timezone.utc)
        if plan is not None:
            job.risk_level = plan.risk.value.lower()
            job.risk_reason = plan.risk_reason
        issue.status = "ESCALATED"

        attempt = PatchAttempt(
            job_id=job.id,
            branch_name="",
            attempt_number=attempt_number,
            status="escalated",
            ai_provider=provider.name if provider else None,
            ai_model=provider.model if provider else None,
            analysis=analysis.model_dump(mode="json") if analysis else None,
            plan=plan.model_dump(mode="json") if plan else None,
            failure_reason=reason,
            started_at=job.created_at,
            completed_at=datetime.now(timezone.utc),
        )
        db.add(attempt)
        await db.commit()
        await PatchService._log(db, job.id, job.repository_id, "ESCALATE", reason, level="WARNING")

    @staticmethod
    async def _fail(db, job, issue, repository_id, attempt_number, reason: str):
        try:
            job.status = "failed"
            job.completed_at = datetime.now(timezone.utc)
            issue.status = "FAILED"
            attempt = PatchAttempt(
                job_id=job.id,
                branch_name="",
                attempt_number=attempt_number,
                status="failed",
                failure_reason=reason,
                started_at=job.created_at,
                completed_at=datetime.now(timezone.utc),
            )
            db.add(attempt)
            await db.commit()
            await PatchService._log(db, job.id, repository_id, "ESCALATE", f"Job failed: {reason}", level="ERROR")
        except Exception:
            logger.exception("Failed to record patch failure state.")

    # ------------------------------------------------------------------ lookups

    @staticmethod
    async def _get_repository(db: AsyncSession, user_id: int, repository_id: int) -> Repository:
        stmt = select(Repository).where(
            Repository.id == repository_id,
            Repository.user_id == user_id,
            Repository.connection_status != "disconnected",
        )
        result = await db.execute(stmt)
        repo = result.scalars().first()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found.")
        return repo

    @staticmethod
    async def _get_issue(db: AsyncSession, repository_id: int, issue_id: int) -> MaintenanceIssue:
        stmt = select(MaintenanceIssue).where(
            MaintenanceIssue.id == issue_id, MaintenanceIssue.repository_id == repository_id
        )
        result = await db.execute(stmt)
        issue = result.scalars().first()
        if not issue:
            raise HTTPException(status_code=404, detail="Maintenance issue not found.")
        return issue

    @staticmethod
    async def _get_job(db: AsyncSession, repository_id: int, job_id: int) -> MaintenanceJob:
        stmt = select(MaintenanceJob).where(MaintenanceJob.id == job_id, MaintenanceJob.repository_id == repository_id)
        result = await db.execute(stmt)
        job = result.scalars().first()
        if not job:
            raise HTTPException(status_code=404, detail="Maintenance job not found.")
        return job

    @staticmethod
    async def _get_dependency(db: AsyncSession, repository_id: int, package_name: Optional[str]) -> Optional[Dependency]:
        if not package_name:
            return None
        stmt = select(Dependency).where(Dependency.repository_id == repository_id, Dependency.name == package_name)
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def _get_readiness(db: AsyncSession, repository_id: int) -> Optional[RepositoryReadiness]:
        stmt = select(RepositoryReadiness).where(RepositoryReadiness.repository_id == repository_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def _next_attempt_number(db: AsyncSession, issue_id: int) -> int:
        stmt = (
            select(MaintenanceJob.id)
            .where(MaintenanceJob.issue_id == issue_id)
        )
        result = await db.execute(stmt)
        job_ids = [row[0] for row in result.all()]
        if not job_ids:
            return 1
        stmt2 = select(PatchAttempt).where(PatchAttempt.job_id.in_(job_ids))
        result2 = await db.execute(stmt2)
        return len(result2.scalars().all()) + 1

    # ------------------------------------------------------------------ response assembly

    @staticmethod
    async def to_response_dict(db: AsyncSession, job: MaintenanceJob) -> dict:
        stmt = select(PatchAttempt).where(PatchAttempt.job_id == job.id).order_by(PatchAttempt.attempt_number)
        result = await db.execute(stmt)
        attempts = result.scalars().all()
        return {
            "id": job.id,
            "repository_id": job.repository_id,
            "issue_id": job.issue_id,
            "status": job.status,
            "risk_level": job.risk_level,
            "risk_reason": job.risk_reason,
            "trigger": job.trigger,
            "decision": job.decision,
            "decision_reason": job.decision_reason,
            "decision_policy": job.decision_policy,
            "decision_matched_rules": job.decision_matched_rules,
            "decision_blocked_by": job.decision_blocked_by,
            "requires_approval": job.requires_approval,
            "approved_at": job.approved_at,
            "rejected_at": job.rejected_at,
            "rejection_reason": job.rejection_reason,
            "blocking_job_id": job.blocking_job_id,
            "created_at": job.created_at,
            "completed_at": job.completed_at,
            "attempts": attempts,
        }
