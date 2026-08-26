from app.services.decision_service import (
    DecisionEngine,
    DecisionInput,
    RepositoryInput,
    IssueInput,
    PatchInput,
    VerificationCapability,
    ConflictInput,
    PolicyInput,
    classify_dependency_bump,
    match_protected_path,
    DECISION_AUTO_EXECUTE,
    DECISION_APPROVAL_REQUIRED,
    DECISION_ESCALATE,
    DECISION_IGNORE,
    DECISION_BLOCKED_BY_CONFLICT,
    UPDATE_TYPE_SECURITY_PATCH,
    UPDATE_TYPE_MAJOR,
)

BALANCED_POLICY = PolicyInput(
    mode="BALANCED",
    security_patch_action="AUTO_EXECUTE",
    patch_update_action="AUTO_EXECUTE",
    minor_update_action="APPROVAL_REQUIRED",
    major_update_action="ESCALATE",
    protected_path_action="APPROVAL_REQUIRED",
    protected_paths=["**/auth/**", "**/payments/**"],
)


def _base_input(**overrides) -> DecisionInput:
    defaults = dict(
        repository=RepositoryInput(status="ACTIVE"),
        issue=IssueInput(category="vulnerability", severity="HIGH"),
        policy=BALANCED_POLICY,
        conflicts=ConflictInput(),
        patch=PatchInput(risk="LOW", update_type=UPDATE_TYPE_SECURITY_PATCH, files=["package.json", "package-lock.json"]),
        verification=VerificationCapability(build_available=True, tests_available=True, security_audit_available=True, readiness_level="HIGH"),
    )
    defaults.update(overrides)
    return DecisionInput(**defaults)


# Case 1: LOW risk security patch, high readiness, verification available, BALANCED -> AUTO_EXECUTE
def test_low_risk_security_patch_auto_executes():
    result = DecisionEngine.evaluate(_base_input())
    assert result.decision == DECISION_AUTO_EXECUTE


# Case 2: MAJOR dependency update -> ESCALATE
def test_major_dependency_update_escalates():
    inp = _base_input(
        issue=IssueInput(category="outdated_dependency", severity="MEDIUM"),
        patch=PatchInput(risk="LOW", update_type=UPDATE_TYPE_MAJOR, files=["package.json"]),
    )
    result = DecisionEngine.evaluate(inp)
    assert result.decision == DECISION_ESCALATE


# Case 3: protected auth file -> APPROVAL_REQUIRED (per BALANCED policy's protected_path_action)
def test_protected_auth_path_requires_approval():
    inp = _base_input(patch=PatchInput(risk="LOW", update_type=UPDATE_TYPE_SECURITY_PATCH, files=["src/auth/session.ts"]))
    result = DecisionEngine.evaluate(inp)
    assert result.decision == DECISION_APPROVAL_REQUIRED
    assert any("PROTECTED_PATH_MATCH" in r for r in result.matched_rules)


# Case 4: repository PAUSED -> blocked (IGNORE, with blocked_by populated) — no
# autonomous action, regardless of risk/policy.
def test_paused_repository_blocks_action():
    inp = _base_input(repository=RepositoryInput(status="PAUSED"))
    result = DecisionEngine.evaluate(inp)
    assert result.decision == DECISION_IGNORE
    assert "REPOSITORY_PAUSED" in result.blocked_by


# Case 5: existing open PR for this issue -> no duplicate work
def test_existing_open_pr_prevents_duplicate_work():
    inp = _base_input(conflicts=ConflictInput(existing_open_pr_number=7))
    result = DecisionEngine.evaluate(inp)
    assert result.decision == DECISION_IGNORE
    assert any("EXISTING_PR:7" in b for b in result.blocked_by)


# Case 6: conflicting active job on the same repository -> BLOCKED_BY_CONFLICT
def test_conflicting_active_job_blocks_with_conflict_id():
    inp = _base_input(conflicts=ConflictInput(active_job_same_repo_id=42))
    result = DecisionEngine.evaluate(inp)
    assert result.decision == DECISION_BLOCKED_BY_CONFLICT
    assert any("CONFLICT:42" in b for b in result.blocked_by)


# Additional coverage: HIGH risk always escalates regardless of policy tier.
def test_high_risk_always_escalates():
    inp = _base_input(patch=PatchInput(risk="HIGH", update_type=UPDATE_TYPE_SECURITY_PATCH, files=["package.json"]))
    result = DecisionEngine.evaluate(inp)
    assert result.decision == DECISION_ESCALATE
    assert "HIGH_RISK" in result.matched_rules


# Additional coverage: MEDIUM risk never silently auto-executes even on an
# auto-execute tier.
def test_medium_risk_never_silently_auto_executes():
    inp = _base_input(patch=PatchInput(risk="MEDIUM", update_type=UPDATE_TYPE_SECURITY_PATCH, files=["package.json"]))
    result = DecisionEngine.evaluate(inp)
    assert result.decision == DECISION_APPROVAL_REQUIRED
    assert "MEDIUM_RISK_REQUIRES_APPROVAL" in result.matched_rules


# Additional coverage: same-issue duplicate active job is treated distinctly
# from a repo-wide conflict, and takes precedence.
def test_duplicate_active_job_same_issue_is_ignored_not_blocked():
    inp = _base_input(conflicts=ConflictInput(active_job_same_issue_id=9, active_job_same_repo_id=9))
    result = DecisionEngine.evaluate(inp)
    assert result.decision == DECISION_IGNORE
    assert "DUPLICATE_ACTIVE_JOB" in result.matched_rules


# Pre-flight pass (no patch info yet) never blocks unless a hard rule fires.
def test_preflight_pass_with_no_patch_info_clears_when_nothing_blocks():
    inp = DecisionInput(
        repository=RepositoryInput(status="ACTIVE"),
        issue=IssueInput(category="vulnerability", severity="HIGH"),
        policy=BALANCED_POLICY,
        conflicts=ConflictInput(),
        patch=None,
        verification=None,
    )
    result = DecisionEngine.evaluate(inp)
    assert result.decision == "PREPARE_ONLY"
    assert result.decision != DECISION_IGNORE


def test_classify_dependency_bump():
    assert classify_dependency_bump("1.2.3", "1.2.9") == "PATCH_DEPENDENCY_UPDATE"
    assert classify_dependency_bump("1.2.3", "1.5.0") == "MINOR_DEPENDENCY_UPDATE"
    assert classify_dependency_bump("1.2.3", "2.0.0") == "MAJOR_DEPENDENCY_UPDATE"
    # Unparseable versions fall back to the safer MINOR classification.
    assert classify_dependency_bump("1.2.3", "latest") == "MINOR_DEPENDENCY_UPDATE"


def test_match_protected_path_glob():
    assert match_protected_path(["src/auth/session.ts"], ["**/auth/**"]) == "**/auth/**"
    assert match_protected_path([".github/workflows/ci.yml"], [".github/workflows/**"]) == ".github/workflows/**"
    assert match_protected_path(["src/utils/format.ts"], ["**/auth/**", "**/payments/**"]) is None
