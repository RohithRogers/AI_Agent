import os
from pathlib import Path
from config import BASE_DIR

# ── Active session registry ────────────────────────────────────────────────────
# Stores the currently active workspace session_id so tools can resolve paths
# without needing session_id passed as an explicit argument.

_active_session_id: str | None = None


def set_active_session(session_id: str | None) -> None:
    """Called by chat_agent when it begins/ends a session."""
    global _active_session_id
    _active_session_id = session_id


def get_active_session() -> str | None:
    """Return the currently active session_id (or None if no session is open)."""
    return _active_session_id


# ── Path helpers ───────────────────────────────────────────────────────────────

def validate_path(path):
    """
    Ensures that the provided path is within the project's BASE_DIR.
    Prevents directory traversal attacks.
    """
    abs_path = os.path.abspath(path)
    if not abs_path.startswith(os.path.abspath(BASE_DIR)):
        raise PermissionError(f"Access denied: Path '{path}' is outside the permitted workspace.")
    return abs_path


def resolve_workspace_path(filename: str, sub: str = "outputs") -> str:
    """
    If an active workspace session exists and *filename* is a bare name
    (no directory component), return the full path inside the session's
    ``outputs/`` (or ``scratch/``) folder.

    If no session is active, or the caller already supplied an absolute /
    relative path, fall back to the original filename (which will then be
    validated by validate_path as usual).

    Parameters
    ----------
    filename : str
        The file name or path supplied by the agent.
    sub : str
        Sub-folder inside the session — ``"outputs"`` (default) or ``"scratch"``.

    Returns
    -------
    str
        Absolute path string suitable for passing to open() or validate_path().
    """
    session_id = get_active_session()
    if session_id and not os.path.dirname(filename):
        # Bare filename → route to workspace session folder
        from tools.workspace_manager import workspace_manager, SESSIONS_DIR
        folder = SESSIONS_DIR / session_id / sub
        folder.mkdir(parents=True, exist_ok=True)
        return str(folder / filename)
    # Already has path separator — validate and return as-is
    return filename
