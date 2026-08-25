import os
import json
from typing import Dict, Any


class ReadinessService:
    """Evaluates repository signals for automated maintenance capability."""

    @classmethod
    def evaluate_repository(cls, repo_path: str) -> Dict[str, Any]:
        manifest_found = False
        lockfile_found = False
        build_script_found = False
        test_script_found = False
        lint_script_found = False
        typecheck_script_found = False
        ci_config_found = False

        if not os.path.exists(repo_path):
            return {
                "manifest_found": False,
                "lockfile_found": False,
                "build_script_found": False,
                "test_script_found": False,
                "lint_script_found": False,
                "typecheck_script_found": False,
                "ci_config_found": False,
                "score_level": "LOW",
                "details": {"reason": "Repository directory path not found"}
            }

        # 1. Manifest & Lockfile Check
        pkg_json_path = os.path.join(repo_path, "package.json")
        req_txt_path = os.path.join(repo_path, "requirements.txt")
        pyproject_path = os.path.join(repo_path, "pyproject.toml")

        if os.path.exists(pkg_json_path) or os.path.exists(req_txt_path) or os.path.exists(pyproject_path):
            manifest_found = True

        for lockfile in ["package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Pipfile.lock"]:
            if os.path.exists(os.path.join(repo_path, lockfile)):
                lockfile_found = True
                break

        # 2. Package.json scripts check
        if os.path.exists(pkg_json_path):
            try:
                with open(pkg_json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    scripts = data.get("scripts", {})
                    if "build" in scripts:
                        build_script_found = True
                    if "test" in scripts or "test:unit" in scripts:
                        test_script_found = True
                    if "lint" in scripts:
                        lint_script_found = True
                    if "type-check" in scripts or "tsc" in scripts or "typecheck" in scripts:
                        typecheck_script_found = True
            except Exception:
                pass

        # 3. CI Config Check
        github_workflows = os.path.join(repo_path, ".github", "workflows")
        gitlab_ci = os.path.join(repo_path, ".gitlab-ci.yml")
        circleci = os.path.join(repo_path, ".circleci")

        if (os.path.exists(github_workflows) and os.listdir(github_workflows)) or os.path.exists(gitlab_ci) or os.path.exists(circleci):
            ci_config_found = True

        # Calculate score
        score_count = sum([
            manifest_found,
            lockfile_found,
            build_script_found,
            test_script_found,
            lint_script_found,
            typecheck_script_found,
            ci_config_found
        ])

        if score_count >= 5:
            score_level = "HIGH"
        elif score_count >= 3:
            score_level = "MEDIUM"
        else:
            score_level = "LOW"

        return {
            "manifest_found": manifest_found,
            "lockfile_found": lockfile_found,
            "build_script_found": build_script_found,
            "test_script_found": test_script_found,
            "lint_script_found": lint_script_found,
            "typecheck_script_found": typecheck_script_found,
            "ci_config_found": ci_config_found,
            "score_level": score_level,
            "details": {
                "signal_count": score_count,
                "total_possible": 7
            }
        }
