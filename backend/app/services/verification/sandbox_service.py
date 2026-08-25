import subprocess
import time
import uuid
from dataclasses import dataclass
from typing import Optional


class SandboxError(Exception):
    pass


@dataclass
class SandboxResult:
    exit_code: Optional[int]  # None means the process was killed for timing out
    stdout: str  # full, untruncated — needed for structured output like `npm audit --json`
    stderr: str  # full, untruncated
    duration_ms: int
    timed_out: bool

    def excerpt(self, limit: int) -> "tuple[str, str]":
        """Tail-truncated (stdout, stderr) for storage/display — a failure's
        useful detail is almost always at the end of the log, but that must
        never be applied before a caller parses structured output."""
        return self.stdout[-limit:], self.stderr[-limit:]


class SandboxService:
    """Runs one verification command inside a disposable, isolated Docker
    container launched via docker-outside-of-docker (the mounted host socket).

    Isolation properties, all load-bearing for Phase 4's security rule:
    - No `-e`/`--env-file` is ever passed, so the container starts with only the
      base image's own environment. TALOS's GITHUB_PERSONAL_ACCESS_TOKEN,
      GEMINI_API_KEY, DATABASE_URL, OLLAMA_BASE_URL, and SECRET_KEY are never
      forwarded — the `docker run` CLI's own environment has no bearing on what
      lands inside the container being launched.
    - `--network bridge` is Docker's default bridge network, which is NOT the
      docker-compose network `postgres`/`backend`/`frontend` communicate over —
      the sandbox cannot resolve or reach any TALOS service by hostname.
    - `--rm` guarantees no container survives past its single command.
    - Memory/CPU/pids limits and a hard wall-clock timeout bound worst-case
      resource usage from untrusted repository code.
    """

    OUTPUT_LIMIT = 4000  # chars kept per stream; stored evidence, not full logs

    @staticmethod
    def check_docker_available() -> bool:
        try:
            proc = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=10)
            return proc.returncode == 0
        except Exception:
            return False

    @classmethod
    def run(
        cls,
        image: str,
        workspace_subdir: str,
        command: str,
        timeout: int,
        memory: str = "1g",
        cpus: str = "1.5",
        run_label: str = "verify",
        volume_name: str = "talos_workspaces",
    ) -> SandboxResult:
        container_name = f"talos-{run_label}-{uuid.uuid4().hex[:10]}"
        docker_cmd = [
            "docker", "run", "--rm",
            "--name", container_name,
            "--network", "bridge",
            "--memory", memory,
            "--cpus", cpus,
            "--pids-limit", "256",
            "--security-opt", "no-new-privileges",
            "-v", f"{volume_name}:/workspaces:rw",
            "-w", f"/workspaces/{workspace_subdir}",
            image,
            "sh", "-c", command,
        ]

        start = time.monotonic()
        try:
            proc = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=timeout)
            duration_ms = int((time.monotonic() - start) * 1000)
            return SandboxResult(
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                duration_ms=duration_ms,
                timed_out=False,
            )
        except subprocess.TimeoutExpired as exc:
            # --rm won't clean up a container killed out from under `docker run`
            # by the client-side timeout, so remove it explicitly.
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True, text=True, timeout=15)
            duration_ms = int((time.monotonic() - start) * 1000)

            def _decode(val) -> str:
                if val is None:
                    return ""
                return val.decode(errors="replace") if isinstance(val, bytes) else val

            return SandboxResult(
                exit_code=None,
                stdout=_decode(exc.stdout),
                stderr=_decode(exc.stderr),
                duration_ms=duration_ms,
                timed_out=True,
            )
        except FileNotFoundError as exc:
            raise SandboxError("The `docker` CLI is not installed in this environment.") from exc
