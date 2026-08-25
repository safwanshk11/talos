import os
import shutil
import subprocess
import tempfile
from typing import Optional
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
    def clone_repository(clone_url: str, branch: str, dest: str, timeout: int = 90) -> None:
        cmd = ["git", "clone", "--depth", "1", "--branch", branch, clone_url, dest]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        if proc.returncode != 0:
            # Fallback: clone default HEAD if the named branch clone failed.
            cmd_alt = ["git", "clone", "--depth", "1", clone_url, dest]
            proc_alt = subprocess.run(cmd_alt, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
            if proc_alt.returncode != 0:
                raise GitWorkspaceError(f"git clone failed: {proc_alt.stderr or proc.stderr}")

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
    def cleanup(workspace: str) -> None:
        if workspace and os.path.exists(workspace):
            shutil.rmtree(workspace, ignore_errors=True)
