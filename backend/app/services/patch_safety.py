import os

# Never allow the model to write into these — regardless of what the plan claims.
PROTECTED_PATH_PARTS = {".git", ".github", "node_modules", ".env", ".venv", "venv"}

MAX_FILE_BYTES = 300_000
MAX_FILES_MODIFIED = 10


class PatchSafetyError(Exception):
    pass


def validate_and_resolve(workspace_path: str, rel_path: str) -> str:
    """Validate a model-proposed relative file path and resolve it to an absolute
    path guaranteed to stay inside the workspace. Repository text (including the
    plan/patch the model itself produced) is untrusted input."""
    if not rel_path or not isinstance(rel_path, str):
        raise PatchSafetyError("Empty or invalid file path.")

    if os.path.isabs(rel_path) or rel_path.startswith("~"):
        raise PatchSafetyError(f"Absolute paths are rejected: {rel_path}")

    normalized = os.path.normpath(rel_path)
    parts = normalized.split(os.sep)

    if normalized.startswith("..") or ".." in parts:
        raise PatchSafetyError(f"Path traversal rejected: {rel_path}")

    if set(parts) & PROTECTED_PATH_PARTS:
        raise PatchSafetyError(f"Protected path rejected: {rel_path}")

    workspace_real = os.path.realpath(workspace_path)
    full_path = os.path.realpath(os.path.join(workspace_real, normalized))

    if full_path != workspace_real and not full_path.startswith(workspace_real + os.sep):
        raise PatchSafetyError(f"Path escapes workspace: {rel_path}")

    return full_path


def enforce_content_limit(content: str, rel_path: str) -> None:
    if len(content.encode("utf-8", errors="ignore")) > MAX_FILE_BYTES:
        raise PatchSafetyError(f"File exceeds size limit ({MAX_FILE_BYTES} bytes): {rel_path}")


def enforce_file_count_limit(count: int) -> None:
    if count > MAX_FILES_MODIFIED:
        raise PatchSafetyError(f"Too many files modified in a single patch attempt ({count} > {MAX_FILES_MODIFIED}).")
