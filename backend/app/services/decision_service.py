"""Phase 6.5: TALOS Decision Engine & Autonomy Governance.

Answers "should TALOS act, and how far?" for a detected maintenance issue —
deterministically. AI may supply structured input (risk classification, files
touched) but never gets a vote on whether autonomous modification is safe;
that decision is made entirely by trusted, database-stored policy evaluated
here, in-process, with no network/AI call. See PHASES.md Phase 6.5.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from app.models.future import MaintenanceJob, PullRequest, ActionLog
from app.models.policy import RepositoryAutomationPolicy, POLICY_PRESETS, DEFAULT_PROTECTED_PATHS

# ---------------------------------------------------------------- decisions

DECISION_AUTO_EXECUTE = "AUTO_EXECUTE"
DECISION_PREPARE_ONLY = "PREPARE_ONLY"
DECISION_APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
DECISION_ESCALATE = "ESCALATE"
DECISION_IGNORE = "IGNORE"
DECISION_BLOCKED_BY_CONFLICT = "BLOCKED_BY_CONFLICT"

UPDATE_TYPE_SECURITY_PATCH = "SECURITY_PATCH"
UPDATE_TYPE_PATCH = "PATCH_DEPENDENCY_UPDATE"
UPDATE_TYPE_MINOR = "MINOR_DEPENDENCY_UPDATE"
UPDATE_TYPE_MAJOR = "MAJOR_DEPENDENCY_UPDATE"

# A job in one of these statuses is genuinely doing in-flight work — used for
# the repository-level lock (Phase 6.5 section 22: one active patch job per
# repository, in preference to file-level collision detection).
ACTIVE_JOB_LOCK_STATUSES = ["analyzing", "planning", "planned", "sandboxing", "patching", "verifying", "delivering"]
# Same-issue duplicate check additionally counts a pending approval as active —
# re-running Prepare Fix on an issue already awaiting approval must not spawn
# a second attempt (this is also the backend enforcement for Phase 6.5 section
# 25: there is no separate "patch endpoint" to bypass — prepare-fix always
# re-runs this same conflict check, so a duplicate call while waiting_for_approval
# is deterministically re-blocked, not silently allowed to proceed).
SAME_ISSUE_LOCK_STATUSES = ACTIVE_JOB_LOCK_STATUSES + ["waiting_for_approval"]

VALID_STANDARD_TIER_ACTIONS = {DECISION_AUTO_EXECUTE, DECISION_PREPARE_ONLY, DECISION_APPROVAL_REQUIRED}
VALID_HARD_TIER_ACTIONS = {DECISION_APPROVAL_REQUIRED, DECISION_ESCALATE}


# ---------------------------------------------------------------- pure data model

@dataclass
class RepositoryInput:
    status: str  # "ACTIVE" | "PAUSED"


@dataclass
class IssueInput:
    category: str
    severity: str


@dataclass
class PatchInput:
    risk: str  # LOW | MEDIUM | HIGH
    update_type: str
    files: List[str] = field(default_factory=list)


@dataclass
class VerificationCapability:
    build_available: bool = False
    tests_available: bool = False
    security_audit_available: bool = False
    readiness_level: str = "LOW"


@dataclass
class ConflictInput:
    active_job_same_issue_id: Optional[int] = None
    active_job_same_repo_id: Optional[int] = None
    existing_open_pr_number: Optional[int] = None


@dataclass
class PolicyInput:
    mode: str
    security_patch_action: str
    patch_update_action: str
    minor_update_action: str
    major_update_action: str
    protected_path_action: str
    protected_paths: List[str] = field(default_factory=list)


@dataclass
class DecisionInput:
    repository: RepositoryInput
    issue: IssueInput
    policy: PolicyInput
    conflicts: ConflictInput = field(default_factory=ConflictInput)
    patch: Optional[PatchInput] = None
    verification: Optional[VerificationCapability] = None


@dataclass
class DecisionResult:
    decision: str
    reason: str
    matched_rules: List[str] = field(default_factory=list)
    blocked_by: List[str] = field(default_factory=list)
    requires_approval: bool = False


# ---------------------------------------------------------------- helpers

def _glob_match(path: str, pattern: str) -> bool:
    """Deterministic path matching for the MVP (Phase 6.5 section 11: "deterministic
    path matching is acceptable"). Supports '**' (any depth) and '*' (single segment)."""
    regex = re.escape(pattern)
    regex = regex.replace(r"\*\*/", "(?:.*/)?").replace(r"\*\*", ".*").replace(r"\*", "[^/]*")
    return re.fullmatch(regex, path.lstrip("/")) is not None


def match_protected_path(files: List[str], patterns: List[str]) -> Optional[str]:
    for f in files:
        for p in patterns:
            if _glob_match(f, p):
                return p
    return None


def _parse_semver(v: Optional[str]):
    if not v:
        return None
    v = v.strip().lstrip("^~>=v ")
    m = re.match(r"(\d+)\.(\d+)\.(\d+)", v)
    return tuple(int(x) for x in m.groups()) if m else None


def classify_dependency_bump(current: Optional[str], target: Optional[str]) -> str:
    """PATCH / MINOR / MAJOR by semver comparison. Falls back to MINOR — not
    PATCH — when either version isn't parseable, since silently under-classifying
    risk is the more dangerous direction to guess wrong in."""
    c, t = _parse_semver(current), _parse_semver(target)
    if not c or not t:
        return UPDATE_TYPE_MINOR
    if t[0] != c[0]:
        return UPDATE_TYPE_MAJOR
    if t[1] != c[1]:
        return UPDATE_TYPE_MINOR
    return UPDATE_TYPE_PATCH


# ---------------------------------------------------------------- the engine

class DecisionEngine:
    """Pure, deterministic, no I/O. See PHASES.md Phase 6.5 section 15 for the
    precedence order this implements: hard safety rules > protected area >
    conflict > user policy > risk > automation readiness."""

    @staticmethod
    def evaluate(inp: DecisionInput) -> DecisionResult:
        # ---- Tier 1: hard safety rules ----
        if inp.repository.status == "PAUSED":
            return DecisionResult(
                decision=DECISION_IGNORE,
                reason="Repository monitoring is paused; TALOS does not act autonomously while paused.",
                matched_rules=["REPOSITORY_PAUSED"],
                blocked_by=["REPOSITORY_PAUSED"],
            )

        if inp.conflicts.active_job_same_issue_id:
            return DecisionResult(
                decision=DECISION_IGNORE,
                reason=f"Issue already has an active maintenance job (#{inp.conflicts.active_job_same_issue_id}); TALOS does not duplicate in-flight work.",
                matched_rules=["DUPLICATE_ACTIVE_JOB"],
                blocked_by=[f"ACTIVE_JOB:{inp.conflicts.active_job_same_issue_id}"],
            )

        if inp.conflicts.existing_open_pr_number:
            return DecisionResult(
                decision=DECISION_IGNORE,
                reason=f"An open pull request (#{inp.conflicts.existing_open_pr_number}) already exists for this issue; TALOS does not open a duplicate.",
                matched_rules=["EXISTING_OPEN_PR"],
                blocked_by=[f"EXISTING_PR:{inp.conflicts.existing_open_pr_number}"],
            )

        if inp.conflicts.active_job_same_repo_id:
            return DecisionResult(
                decision=DECISION_BLOCKED_BY_CONFLICT,
                reason=f"Repository has a conflicting active maintenance job (#{inp.conflicts.active_job_same_repo_id}); TALOS processes one patch job per repository at a time.",
                matched_rules=["REPOSITORY_LOCK"],
                blocked_by=[f"CONFLICT:{inp.conflicts.active_job_same_repo_id}"],
            )

        # Pre-flight pass (called before cloning/AI cost): no patch/risk info
        # yet, and nothing hard blocked — clear to proceed with analysis.
        if inp.patch is None:
            return DecisionResult(
                decision=DECISION_PREPARE_ONLY,
                reason="No hard safety rule blocked this issue; proceeding to analysis and planning.",
                matched_rules=["PREFLIGHT_CLEAR"],
            )

        if inp.patch.risk == "HIGH":
            return DecisionResult(
                decision=DECISION_ESCALATE,
                reason="Risk classified HIGH; TALOS does not autonomously patch HIGH-risk changes.",
                matched_rules=["HIGH_RISK"],
            )

        # ---- Tier 2: protected area rule ----
        matched_pattern = match_protected_path(inp.patch.files, inp.policy.protected_paths)
        if matched_pattern:
            action = inp.policy.protected_path_action
            return DecisionResult(
                decision=action,
                reason=f"Proposed changes touch a protected path ({matched_pattern}); policy requires {action.replace('_', ' ').lower()}.",
                matched_rules=[f"PROTECTED_PATH_MATCH:{matched_pattern}"],
                requires_approval=(action == DECISION_APPROVAL_REQUIRED),
            )

        # ---- Tier 3: user policy (risk-tier action lookup) ----
        matched: List[str] = []
        tier_action_map = {
            UPDATE_TYPE_SECURITY_PATCH: inp.policy.security_patch_action,
            UPDATE_TYPE_PATCH: inp.policy.patch_update_action,
            UPDATE_TYPE_MINOR: inp.policy.minor_update_action,
            UPDATE_TYPE_MAJOR: inp.policy.major_update_action,
        }
        action = tier_action_map.get(inp.patch.update_type, DECISION_APPROVAL_REQUIRED)
        matched.append(f"POLICY_TIER:{inp.patch.update_type}:{action}")

        # Medium risk never silently auto-executes, even on an auto-execute tier.
        if action == DECISION_AUTO_EXECUTE and inp.patch.risk == "MEDIUM":
            action = DECISION_APPROVAL_REQUIRED
            matched.append("MEDIUM_RISK_REQUIRES_APPROVAL")

        # ---- Tier 4: automation readiness / verification capability ----
        if action == DECISION_AUTO_EXECUTE and inp.verification is not None:
            if inp.verification.readiness_level == "LOW" and inp.patch.risk in ("MEDIUM", "HIGH"):
                action = DECISION_APPROVAL_REQUIRED
                matched.append("VERIFICATION_CAPABILITY_INSUFFICIENT")
            elif not inp.verification.build_available and not inp.verification.tests_available:
                action = DECISION_APPROVAL_REQUIRED
                matched.append("NO_VERIFICATION_CAPABILITY")

        return DecisionResult(
            decision=action,
            reason=DecisionEngine._explain(action, inp),
            matched_rules=matched,
            requires_approval=(action == DECISION_APPROVAL_REQUIRED),
        )

    @staticmethod
    def _explain(action: str, inp: DecisionInput) -> str:
        label = inp.patch.update_type.replace("_", " ").title()
        if action == DECISION_AUTO_EXECUTE:
            return f"{label} classified {inp.patch.risk} risk, permitted by {inp.policy.mode} policy with no protected files or conflicts."
        if action == DECISION_ESCALATE:
            return f"{label} requires human review under {inp.policy.mode} policy."
        if action == DECISION_APPROVAL_REQUIRED:
            return f"{label} ({inp.patch.risk} risk) requires developer approval under {inp.policy.mode} policy."
        if action == DECISION_PREPARE_ONLY:
            return f"{label} ({inp.patch.risk} risk) permitted to prepare under {inp.policy.mode} policy; verification and delivery require a manual next step."
        return f"{label} ({inp.patch.risk} risk) evaluated under {inp.policy.mode} policy."


# ---------------------------------------------------------------- policy persistence

class PolicyService:
    @staticmethod
    async def get_or_create(db: AsyncSession, repository_id: int) -> RepositoryAutomationPolicy:
        stmt = select(RepositoryAutomationPolicy).where(RepositoryAutomationPolicy.repository_id == repository_id)
        res = await db.execute(stmt)
        policy = res.scalars().first()
        if policy:
            return policy
        policy = RepositoryAutomationPolicy(
            repository_id=repository_id,
            protected_paths=list(DEFAULT_PROTECTED_PATHS),
            mode="BALANCED",
            **POLICY_PRESETS["BALANCED"],
        )
        db.add(policy)
        await db.commit()
        await db.refresh(policy)
        return policy

    @staticmethod
    def to_policy_input(policy: RepositoryAutomationPolicy) -> PolicyInput:
        return PolicyInput(
            mode=policy.mode,
            security_patch_action=policy.security_patch_action,
            patch_update_action=policy.patch_update_action,
            minor_update_action=policy.minor_update_action,
            major_update_action=policy.major_update_action,
            protected_path_action=policy.protected_path_action,
            protected_paths=policy.protected_paths or [],
        )

    @staticmethod
    async def apply_preset(db: AsyncSession, policy: RepositoryAutomationPolicy, mode: str) -> RepositoryAutomationPolicy:
        if mode not in POLICY_PRESETS:
            raise HTTPException(status_code=400, detail=f"Invalid automation mode '{mode}'.")
        policy.mode = mode
        for key, value in POLICY_PRESETS[mode].items():
            setattr(policy, key, value)
        await db.commit()
        await db.refresh(policy)
        return policy

    @staticmethod
    async def update(db: AsyncSession, policy: RepositoryAutomationPolicy, payload) -> RepositoryAutomationPolicy:
        """Deliberately narrow: a handful of dropdowns, not a policy language
        (Phase 6.5 section 8/46). Major-update and protected-path actions can
        never be set to AUTO_EXECUTE, regardless of mode — enforced here, not
        just hidden in the UI."""
        if payload.mode is not None:
            return await PolicyService.apply_preset(db, policy, payload.mode)

        if payload.security_patch_action is not None:
            if payload.security_patch_action not in VALID_STANDARD_TIER_ACTIONS:
                raise HTTPException(status_code=400, detail="Invalid security patch action.")
            policy.security_patch_action = payload.security_patch_action

        if payload.patch_update_action is not None:
            if payload.patch_update_action not in VALID_STANDARD_TIER_ACTIONS:
                raise HTTPException(status_code=400, detail="Invalid patch update action.")
            policy.patch_update_action = payload.patch_update_action

        if payload.minor_update_action is not None:
            if payload.minor_update_action not in VALID_STANDARD_TIER_ACTIONS:
                raise HTTPException(status_code=400, detail="Invalid minor update action.")
            policy.minor_update_action = payload.minor_update_action

        if payload.major_update_action is not None:
            if payload.major_update_action not in VALID_HARD_TIER_ACTIONS:
                raise HTTPException(status_code=400, detail="Major dependency updates can never be set to Auto Execute or Prepare Only.")
            policy.major_update_action = payload.major_update_action

        if payload.protected_path_action is not None:
            if payload.protected_path_action not in VALID_HARD_TIER_ACTIONS:
                raise HTTPException(status_code=400, detail="Protected-path action can never be set to Auto Execute or Prepare Only.")
            policy.protected_path_action = payload.protected_path_action

        if payload.protected_paths is not None:
            policy.protected_paths = payload.protected_paths

        await db.commit()
        await db.refresh(policy)
        return policy


# ---------------------------------------------------------------- conflict detection

class ConflictService:
    @staticmethod
    async def check(db: AsyncSession, repository_id: int, issue_id: int, exclude_job_id: int) -> ConflictInput:
        same_issue_stmt = select(MaintenanceJob).where(
            MaintenanceJob.issue_id == issue_id,
            MaintenanceJob.id != exclude_job_id,
            MaintenanceJob.status.in_(SAME_ISSUE_LOCK_STATUSES),
        )
        same_issue = (await db.execute(same_issue_stmt)).scalars().first()

        same_repo_stmt = select(MaintenanceJob).where(
            MaintenanceJob.repository_id == repository_id,
            MaintenanceJob.id != exclude_job_id,
            MaintenanceJob.status.in_(ACTIVE_JOB_LOCK_STATUSES),
        )
        same_repo = (await db.execute(same_repo_stmt)).scalars().first()

        pr_stmt = (
            select(PullRequest)
            .join(MaintenanceJob, PullRequest.maintenance_job_id == MaintenanceJob.id)
            .where(
                MaintenanceJob.issue_id == issue_id,
                PullRequest.status == "delivered",
                PullRequest.github_status == "open",
            )
        )
        existing_pr = (await db.execute(pr_stmt)).scalars().first()

        return ConflictInput(
            active_job_same_issue_id=same_issue.id if same_issue else None,
            active_job_same_repo_id=same_repo.id if same_repo else None,
            existing_open_pr_number=existing_pr.pr_number if existing_pr else None,
        )


# ---------------------------------------------------------------- orchestration

class DecisionService:
    """Wires DecisionEngine to the database: builds the input from real rows,
    persists the result onto the job, and writes real Action Ledger entries
    (Phase 6.5 section 33) — never a fabricated confidence score, only the
    rules that actually matched."""

    @staticmethod
    async def _log(db: AsyncSession, job_id: int, repository_id: int, message: str, level: str = "INFO"):
        entry = ActionLog(
            repository_id=repository_id, job_id=job_id, step="DECIDE",
            message=message, level=level, timestamp=datetime.now(timezone.utc),
        )
        db.add(entry)
        await db.commit()

    @staticmethod
    async def decide(
        db: AsyncSession,
        repo,
        issue,
        job: MaintenanceJob,
        policy: RepositoryAutomationPolicy,
        patch: Optional[PatchInput],
        verification: Optional[VerificationCapability],
    ) -> DecisionResult:
        conflicts = await ConflictService.check(db, repo.id, issue.id, exclude_job_id=job.id)
        inp = DecisionInput(
            repository=RepositoryInput(status="PAUSED" if repo.monitoring_status == "paused" else "ACTIVE"),
            issue=IssueInput(category=issue.category, severity=issue.severity),
            policy=PolicyService.to_policy_input(policy),
            conflicts=conflicts,
            patch=patch,
            verification=verification,
        )
        result = DecisionEngine.evaluate(inp)

        job.decision = result.decision
        job.decision_reason = result.reason
        job.decision_policy = policy.mode
        job.decision_matched_rules = result.matched_rules
        job.decision_blocked_by = result.blocked_by
        job.requires_approval = result.requires_approval
        if result.decision == DECISION_BLOCKED_BY_CONFLICT:
            job.blocking_job_id = conflicts.active_job_same_repo_id
        await db.commit()

        await DecisionService._log(db, job.id, repo.id, f"Repository policy loaded: {policy.mode}.")
        for rule in result.matched_rules:
            await DecisionService._log(db, job.id, repo.id, f"Rule evaluated: {rule}")
        level = "WARNING" if result.decision in (DECISION_ESCALATE, DECISION_IGNORE, DECISION_BLOCKED_BY_CONFLICT) else "INFO"
        await DecisionService._log(db, job.id, repo.id, f"Decision: {result.decision} — {result.reason}", level=level)
        return result
