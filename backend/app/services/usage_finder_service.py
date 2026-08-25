import os
import re
from typing import List


class UsageFinderService:
    """Finds files in a cloned repository that import or reference a target dependency package."""

    SKIP_DIRS = {".git", "node_modules", "dist", "build", "venv", ".next", "coverage", "__pycache__"}
    SUPPORTED_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".py"}

    @classmethod
    def find_package_usages(cls, repo_path: str, package_name: str) -> List[str]:
        matching_files: List[str] = []
        if not os.path.exists(repo_path) or not package_name:
            return matching_files

        # Escape package name for regex search
        escaped_pkg = re.escape(package_name)

        # JS/TS import & require patterns
        # e.g., import x from 'pkg', import { x } from "pkg/sub", require('pkg')
        js_pattern = re.compile(
            rf"""(?:import\s+.*?from\s+['"]{escaped_pkg}(?:/.*?)?['"]|require\s*\(\s*['"]{escaped_pkg}(?:/.*?)?['"]\s*\)|import\s*['"]{escaped_pkg}(?:/.*?)?['"])"""
        )

        # Python import pattern
        # e.g., import pkg, from pkg import x, from pkg.sub import x
        py_pkg = package_name.replace("-", "_")
        escaped_py_pkg = re.escape(py_pkg)
        py_pattern = re.compile(
            rf"""(?:import\s+{escaped_py_pkg}(?:\..*?)?|from\s+{escaped_py_pkg}(?:\..*?)?\s+import)"""
        )

        for root, dirs, files in os.walk(repo_path):
            # Skip irrelevant directories
            dirs[:] = [d for d in dirs if d not in cls.SKIP_DIRS]

            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext not in cls.SUPPORTED_EXTENSIONS:
                    continue

                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, repo_path)

                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read(50000)  # Read first 50KB

                    if ext == ".py":
                        if py_pattern.search(content):
                            matching_files.append(rel_path)
                    else:
                        if js_pattern.search(content):
                            matching_files.append(rel_path)
                except Exception:
                    continue

        return matching_files
