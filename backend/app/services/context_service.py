import json
import os
from dataclasses import dataclass, field
from typing import List, Optional

# Total prompt budget for a maintenance context package. Kept small deliberately —
# TALOS must not send the whole repository to the model, only what's relevant.
MAX_CONTEXT_CHARS = 12000
MAX_FILE_EXCERPT_CHARS = 3000
MAX_AFFECTED_FILES = 5
TEST_SEARCH_LIMIT = 5


@dataclass
class ContextSection:
    name: str
    reason: str
    content: str
    priority: int  # lower = kept first when trimming to budget


@dataclass
class MaintenanceContext:
    sections: List[ContextSection] = field(default_factory=list)

    @property
    def total_chars(self) -> int:
        return sum(len(s.content) for s in self.sections)

    def to_prompt(self) -> str:
        parts = []
        for section in self.sections:
            parts.append(
                f"### {section.name}\n(why included: {section.reason})\n{section.content}\n"
            )
        return "\n".join(parts)


def _read_excerpt(path: str, limit: int = MAX_FILE_EXCERPT_CHARS) -> Optional[str]:
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(limit + 1)
        if len(content) > limit:
            content = content[:limit] + "\n... [truncated]"
        return content
    except Exception:
        return None


class ContextEngine:
    """Builds a targeted Maintenance Context Package from Phase 2's repository
    intelligence (the issue, its affected files, the manifest) instead of sending
    the model the whole repository."""

    @classmethod
    def build_context(
        cls,
        issue,
        workspace_path: str,
        readiness=None,
        max_chars: int = MAX_CONTEXT_CHARS,
    ) -> MaintenanceContext:
        sections: List[ContextSection] = []

        # 1. The issue itself — always kept, highest priority.
        sections.append(ContextSection(
            name="maintenance_issue",
            reason="The detected issue TALOS must resolve.",
            content=json.dumps({
                "title": issue.title,
                "description": issue.description,
                "severity": issue.severity,
                "package_name": issue.package_name,
                "current_version": issue.current_version,
                "affected_range": issue.affected_range,
                "recommended_version": issue.recommended_version,
                "advisory_id": issue.advisory_id,
                "source": issue.source,
            }, indent=2),
            priority=0,
        ))

        # 2. Manifest (package.json / requirements.txt) — needed to know exact
        # declared version syntax and available scripts.
        manifest_name = None
        for candidate in ("package.json", "requirements.txt", "pyproject.toml"):
            if os.path.isfile(os.path.join(workspace_path, candidate)):
                manifest_name = candidate
                break

        if manifest_name:
            excerpt = _read_excerpt(os.path.join(workspace_path, manifest_name))
            if excerpt:
                sections.append(ContextSection(
                    name=f"manifest:{manifest_name}",
                    reason="Declares the vulnerable dependency and its version constraint.",
                    content=excerpt,
                    priority=1,
                ))

        # 3. Lockfile presence (metadata only, not content — lockfiles are huge and
        # are updated deterministically by the package manager, not by the model).
        lockfiles_present = [
            lf for lf in ("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Pipfile.lock")
            if os.path.isfile(os.path.join(workspace_path, lf))
        ]
        if lockfiles_present:
            sections.append(ContextSection(
                name="lockfile_info",
                reason="Confirms a lockfile exists that will be deterministically updated by the package manager (not by you).",
                content=json.dumps({"lockfiles_present": lockfiles_present}),
                priority=3,
            ))

        # 4. Affected files — actual source files that import/require the vulnerable package.
        affected_files = (issue.affected_files or [])[:MAX_AFFECTED_FILES]
        for rel_path in affected_files:
            full_path = os.path.join(workspace_path, rel_path)
            excerpt = _read_excerpt(full_path)
            if excerpt is not None:
                sections.append(ContextSection(
                    name=f"affected_file:{rel_path}",
                    reason=f"References {issue.package_name} directly (import/require detected by Phase 2 scan).",
                    content=excerpt,
                    priority=2,
                ))

        # 5. Relevant tests — simple filename heuristic, kept small and low priority.
        test_hits = cls._find_related_tests(workspace_path, issue.package_name)
        for rel_path in test_hits:
            excerpt = _read_excerpt(os.path.join(workspace_path, rel_path), limit=1500)
            if excerpt is not None:
                sections.append(ContextSection(
                    name=f"related_test:{rel_path}",
                    reason="Filename suggests it may exercise the affected component.",
                    content=excerpt,
                    priority=4,
                ))

        # 6. Automation readiness signals — low priority, helps the model know what
        # verification tooling actually exists in this repo.
        if readiness is not None:
            sections.append(ContextSection(
                name="repository_readiness",
                reason="What build/test/lint tooling Phase 2 detected in this repository.",
                content=json.dumps({
                    "build_script_found": readiness.build_script_found,
                    "test_script_found": readiness.test_script_found,
                    "lint_script_found": readiness.lint_script_found,
                    "typecheck_script_found": readiness.typecheck_script_found,
                    "score_level": readiness.score_level,
                }),
                priority=5,
            ))

        return cls._trim_to_budget(sections, max_chars)

    @staticmethod
    def _find_related_tests(workspace_path: str, package_name: Optional[str]) -> List[str]:
        if not package_name:
            return []
        skip_dirs = {".git", "node_modules", "dist", "build", "venv", ".next", "coverage", "__pycache__"}
        hits: List[str] = []
        for root, dirs, files in os.walk(workspace_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for fname in files:
                lower = fname.lower()
                if ("test" in lower or "spec" in lower) and package_name.lower() in lower:
                    rel = os.path.relpath(os.path.join(root, fname), workspace_path)
                    hits.append(rel)
                    if len(hits) >= TEST_SEARCH_LIMIT:
                        return hits
        return hits

    @staticmethod
    def _trim_to_budget(sections: List[ContextSection], max_chars: int) -> MaintenanceContext:
        ordered = sorted(sections, key=lambda s: s.priority)
        kept: List[ContextSection] = []
        used = 0
        for section in ordered:
            remaining = max_chars - used
            if remaining <= 0:
                break
            if len(section.content) > remaining:
                section = ContextSection(
                    name=section.name,
                    reason=section.reason,
                    content=section.content[:remaining] + "\n... [truncated to fit context budget]",
                    priority=section.priority,
                )
            kept.append(section)
            used += len(section.content)
        return MaintenanceContext(sections=kept)
