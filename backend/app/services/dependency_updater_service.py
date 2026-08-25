import os
import re
import subprocess

import httpx


class DependencyUpdateError(Exception):
    pass


PYPI_JSON_URL = "https://pypi.org/pypi/{package}/json"


class DependencyUpdaterService:
    """Deterministic package-manager operations. The AI model decides WHAT needs
    changing (target package/version); this service performs the actual edit so
    the model never hand-invents lockfile contents."""

    @staticmethod
    def update_npm_dependency(
        workspace: str,
        package_name: str,
        target_version: str,
        dep_type: str = "dependencies",
        timeout: int = 120,
    ) -> None:
        if not os.path.isfile(os.path.join(workspace, "package.json")):
            raise DependencyUpdateError("package.json not found in workspace.")

        save_flag = "--save-dev" if dep_type == "devDependencies" else "--save"
        cmd = [
            "npm", "install", f"{package_name}@{target_version}",
            save_flag, "--package-lock-only", "--no-audit", "--no-fund",
        ]
        try:
            proc = subprocess.run(cmd, cwd=workspace, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise DependencyUpdateError(f"npm install timed out after {timeout}s") from exc
        except FileNotFoundError as exc:
            raise DependencyUpdateError("npm is not installed in this environment.") from exc

        if proc.returncode != 0:
            raise DependencyUpdateError(f"npm install failed: {(proc.stderr or proc.stdout)[-2000:]}")

    @staticmethod
    def _resolve_pypi_latest(package_name: str, timeout: int = 15) -> str:
        """pip has no 'latest' tag like npm does — requirements.txt needs a concrete
        pinned version, so resolve it deterministically against the PyPI index."""
        try:
            resp = httpx.get(PYPI_JSON_URL.format(package=package_name), timeout=timeout)
            resp.raise_for_status()
            version = resp.json().get("info", {}).get("version")
        except httpx.HTTPError as exc:
            raise DependencyUpdateError(f"Failed to resolve latest PyPI version for {package_name}: {exc}") from exc
        if not version:
            raise DependencyUpdateError(f"PyPI returned no version info for {package_name}.")
        return version

    @staticmethod
    def update_pip_requirement(workspace: str, package_name: str, target_version: str) -> None:
        req_path = os.path.join(workspace, "requirements.txt")
        if not os.path.isfile(req_path):
            raise DependencyUpdateError("requirements.txt not found in workspace.")

        if target_version.lower() == "latest":
            target_version = DependencyUpdaterService._resolve_pypi_latest(package_name)

        with open(req_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        pattern = re.compile(rf"^\s*{re.escape(package_name)}\s*==", re.IGNORECASE)
        updated = False
        new_lines = []
        for line in lines:
            if pattern.match(line):
                new_lines.append(f"{package_name}=={target_version}\n")
                updated = True
            else:
                new_lines.append(line)

        if not updated:
            raise DependencyUpdateError(f"'{package_name}' not found as a pinned entry in requirements.txt.")

        with open(req_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
