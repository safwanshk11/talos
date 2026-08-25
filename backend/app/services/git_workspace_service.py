import os
import shutil
import subprocess
import tempfile
from typing import Optional
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

WORKSPACE_ROOT = os.environ.get("TALOS_WORKSPACE_ROOT") or os.path.join(tempfile.gettempdir(), "talos_workspaces")


class GitWorkspaceError(Exception):
    pass


class GitWorkspaceService:
    """Manages isolated git clones TALOS patches into. The user's actual GitHub
    repository is never touched — no push ever happens here (Phase 3 stops at a
    local commit on a local branch inside a disposable clone)."""

    @staticmethod
    def create_workspace(job_id: int) -> str:
        os.makedirs(WORKSPACE_ROOT, exist_ok=True)
        path = os.path.join(WORKSPACE_ROOT, f"job_{job_id}_{uuid4().hex[:8]}")
        os.makedirs(path, exist_ok=False)
        return path

    @staticmethod
    def _strip_credentials(url: str) -> str:
        """Returns `url` with any embedded userinfo (e.g. x-access-token:TOKEN@)
        removed. Used immediately after cloning so the token used to authenticate
        a private-repo clone never sits at rest in the workspace's .git/config —
        that config lives inside the shared `talos_workspaces` volume, which
        Phase 4's verification sandbox mounts read-write."""
        parts = urlsplit(url)
        if not parts.username and not parts.password:
            return url
        netloc = parts.hostname or ""
        if parts.port:
            netloc += f":{parts.port}"
        return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))

    @staticmethod
    def clone_repository(clone_url: str, branch: str, dest: str, timeout: int = 90) -> None:
        cmd = ["git", "clone", "--depth", "1", "--branch", branch, clone_url, dest]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        if proc.returncode != 0:
            # Fallback: clone default HEAD if the named branch clone failed.
            cmd_alt = ["git", "clone", "--depth", "1", clone_url, dest]
            proc_alt = subprocess.run(cmd_alt, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
            if proc_alt.returncode != 0:
                raise GitWorkspaceError(f"git clone failed: {proc_alt.stderr or proc.stderr}")

        sanitized = GitWorkspaceService._strip_credentials(clone_url)
        if sanitized != clone_url:
            subprocess.run(["git", "remote", "set-url", "origin", sanitized], cwd=dest, check=True, capture_output=True)

    @staticmethod
    def configure_identity(workspace: str) -> None:
        subprocess.run(["git", "config", "user.email", "talos@talos.internal"], cwd=workspace, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "TALOS Bot"], cwd=workspace, check=True, capture_output=True)

    @staticmethod
    def get_head_sha(workspace: str) -> str:
        proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=workspace, capture_output=True, text=True)
        if proc.returncode != 0:
            raise GitWorkspaceError(f"failed to read HEAD: {proc.stderr}")
        return proc.stdout.strip()

    @staticmethod
    def create_branch(workspace: str, branch_name: str) -> None:
        proc = subprocess.run(["git", "checkout", "-b", branch_name], cwd=workspace, capture_output=True, text=True)
        if proc.returncode != 0:
            raise GitWorkspaceError(f"branch creation failed: {proc.stderr}")

    @staticmethod
    def commit_all(workspace: str, message: str) -> Optional[str]:
        subprocess.run(["git", "add", "-A"], cwd=workspace, check=True, capture_output=True)
        status = subprocess.run(["git", "status", "--porcelain"], cwd=workspace, capture_output=True, text=True)
        if not status.stdout.strip():
            return None
        proc = subprocess.run(["git", "commit", "-m", message], cwd=workspace, capture_output=True, text=True)
        if proc.returncode != 0:
            raise GitWorkspaceError(f"commit failed: {proc.stderr}")
        return GitWorkspaceService.get_head_sha(workspace)

    @staticmethod
    def diff_against_sha(workspace: str, base_sha: str) -> str:
        proc = subprocess.run(["git", "diff", base_sha, "HEAD"], cwd=workspace, capture_output=True, text=True)
        if proc.returncode != 0:
            raise GitWorkspaceError(f"diff generation failed: {proc.stderr}")
        return proc.stdout

    @staticmethod
    def get_current_branch(workspace: str) -> str:
        proc = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=workspace, capture_output=True, text=True)
        if proc.returncode != 0:
            raise GitWorkspaceError(f"failed to read current branch: {proc.stderr}")
        return proc.stdout.strip()

    @staticmethod
    def push_branch(workspace: str, authed_url: str, branch: str, token: str = "", timeout: int = 60) -> None:
        """Pushes HEAD to `branch` on the remote at `authed_url`. The credentialed
        URL is passed directly to this one `git push` invocation and is never
        written to .git/config, so the workspace's `origin` remote (visible inside
        the verification sandbox) stays credential-free before and after this call.

        Force-push is safe and intentional here: TALOS exclusively owns branches
        under its own `talos/fix-*` prefix (never main/default), and idempotent
        retries of a partially-failed delivery must be able to re-push the same
        verified commit without failing on a stale remote ref.
        """
        proc = subprocess.run(
            ["git", "push", "--force", authed_url, f"HEAD:refs/heads/{branch}"],
            cwd=workspace, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout,
        )
        if proc.returncode != 0:
            stderr = proc.stderr or ""
            if token:
                stderr = stderr.replace(token, "***TOKEN***")
            raise GitWorkspaceError(f"git push failed: {stderr}")

    @staticmethod
    def cleanup(workspace: str) -> None:
        if workspace and os.path.exists(workspace):
            shutil.rmtree(workspace, ignore_errors=True)
