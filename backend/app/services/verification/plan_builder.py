import json
import os
from dataclasses import dataclass
from typing import List, Optional

CHECK_ORDER = ["INSTALL", "BUILD", "TYPECHECK", "LINT", "TEST", "SECURITY_AUDIT", "VULNERABILITY_RESCAN"]
REQUIRED_CHECKS = {"INSTALL", "BUILD", "TEST", "VULNERABILITY_RESCAN"}


@dataclass
class PlannedCheck:
    type: str
    command: Optional[str]  # None => not applicable to this repo; recorded as SKIPPED
    required: bool
    skip_reason: Optional[str] = None


class VerificationPlanBuilder:
    """Builds an ordered, repository-specific VerificationPlan from what the
    workspace actually contains — never invents a command that doesn't exist.
    Sourced from the manifest's real scripts, not from Phase 2's cached
    readiness booleans, since running the correct script *name* matters."""

    @classmethod
    def build(cls, workspace_path: str, ecosystem: str) -> List[PlannedCheck]:
        if ecosystem == "npm":
            return cls._build_npm(workspace_path)
        if ecosystem == "pip":
            return cls._build_pip(workspace_path)
        return [
            PlannedCheck(t, None, t in REQUIRED_CHECKS, f"Unsupported ecosystem '{ecosystem}'.")
            for t in CHECK_ORDER
        ]

    @classmethod
    def _build_npm(cls, workspace_path: str) -> List[PlannedCheck]:
        pkg_path = os.path.join(workspace_path, "package.json")
        scripts = {}
        if os.path.isfile(pkg_path):
            try:
                with open(pkg_path, "r", encoding="utf-8") as f:
                    scripts = json.load(f).get("scripts", {}) or {}
            except Exception:
                scripts = {}

        checks: List[PlannedCheck] = []

        has_lockfile = os.path.isfile(os.path.join(workspace_path, "package-lock.json"))
        checks.append(PlannedCheck("INSTALL", "npm ci" if has_lockfile else "npm install", True))

        if "build" in scripts:
            checks.append(PlannedCheck("BUILD", "npm run build", True))
        else:
            checks.append(PlannedCheck("BUILD", None, True, "No 'build' script in package.json."))

        tc_script = next((s for s in ("typecheck", "type-check", "tsc") if s in scripts), None)
        if tc_script:
            checks.append(PlannedCheck("TYPECHECK", f"npm run {tc_script}", False))
        else:
            checks.append(PlannedCheck("TYPECHECK", None, False, "No typecheck script in package.json."))

        if "lint" in scripts:
            checks.append(PlannedCheck("LINT", "npm run lint", False))
        else:
            checks.append(PlannedCheck("LINT", None, False, "No 'lint' script in package.json."))

        test_script = next((s for s in ("test", "test:unit") if s in scripts), None)
        if test_script:
            checks.append(PlannedCheck("TEST", f"npm run {test_script}", True))
        else:
            checks.append(PlannedCheck("TEST", None, True, "No test script in package.json."))

        checks.append(PlannedCheck("SECURITY_AUDIT", "npm audit --json", False))
        checks.append(PlannedCheck("VULNERABILITY_RESCAN", "__internal_osv_rescan__", True))
        return checks

    @classmethod
    def _build_pip(cls, workspace_path: str) -> List[PlannedCheck]:
        checks: List[PlannedCheck] = []

        req_path = os.path.join(workspace_path, "requirements.txt")
        if os.path.isfile(req_path):
            checks.append(PlannedCheck("INSTALL", "pip install -r requirements.txt", True))
        else:
            checks.append(PlannedCheck("INSTALL", None, True, "No requirements.txt found."))

        checks.append(PlannedCheck("BUILD", None, True, "No build step is defined for plain pip projects."))
        checks.append(PlannedCheck("TYPECHECK", None, False, "No typecheck tool configured."))
        checks.append(PlannedCheck("LINT", None, False, "No lint tool configured."))

        has_tests = os.path.isdir(os.path.join(workspace_path, "tests")) or any(
            f.startswith("test_") and f.endswith(".py")
            for f in os.listdir(workspace_path)
            if os.path.isfile(os.path.join(workspace_path, f))
        )
        if has_tests:
            checks.append(PlannedCheck("TEST", "pip install -q pytest && pytest -q", True))
        else:
            checks.append(PlannedCheck("TEST", None, True, "No tests/ directory or test_*.py files found."))

        checks.append(PlannedCheck("SECURITY_AUDIT", None, False, "No deterministic pip audit tool available in the sandbox image."))
        checks.append(PlannedCheck("VULNERABILITY_RESCAN", "__internal_osv_rescan__", True))
        return checks
