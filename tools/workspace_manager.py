"""
workspace_manager.py
--------------------
Manages the agent's sandboxed workspace.

Layout
------
workspace/
├── sessions/<conv_id>/
│   ├── outputs/        ← persistent artefacts (PDFs, docs, etc.)
│   ├── scratch/        ← always wiped at session end
│   ├── venv/           ← per-conversation isolated venv
│   └── meta.json       ← session metadata
├── persistent/
│   └── exports/        ← long-lived artefacts the user keeps
└── workspace.log       ← append-only audit trail

Decisions applied from plan review
-----------------------------------
- Session granularity  : per conversation (not per message)
- Venv                 : per conversation (shared across messages in same conv)
- Keep/delete policy   : persistent by default; inferred from request context
- Max workspace size   : 100 MB — oldest sessions auto-purged on begin
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timezone

from config import BASE_DIR

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
WORKSPACE_ROOT = Path(BASE_DIR) / "workspace"
SESSIONS_DIR   = WORKSPACE_ROOT / "sessions"
PERSISTENT_DIR = WORKSPACE_ROOT / "persistent" / "exports"
LOG_FILE       = WORKSPACE_ROOT / "workspace.log"
MAX_WORKSPACE_BYTES = 100 * 1024 * 1024  # 100 MB


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _dir_size(path: Path) -> int:
    """Return total byte size of a directory tree."""
    total = 0
    for entry in path.rglob("*"):
        if entry.is_file():
            try:
                total += entry.stat().st_size
            except OSError:
                pass
    return total


def _session_mtime(session_path: Path) -> float:
    """Return modification time of a session's meta.json (or 0)."""
    meta = session_path / "meta.json"
    try:
        return meta.stat().st_mtime
    except OSError:
        return 0.0


# ─────────────────────────────────────────────
# WorkspaceManager
# ─────────────────────────────────────────────

class WorkspaceManager:
    """
    Singleton-friendly manager for the agent workspace.

    Usage
    -----
    workspace = WorkspaceManager()
    workspace.begin_session("conv-abc123")
    path = workspace.get_output_path("conv-abc123", "report.pdf")
    workspace.end_session("conv-abc123", keep_outputs=True)
    """

    def __init__(self):
        WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        PERSISTENT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Audit log ──────────────────────────────

    def log(self, session_id: str, action: str, detail: str = "") -> None:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        line = f"[{timestamp}] [{session_id}] {action}"
        if detail:
            line += f" | {detail}"
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass  # Non-fatal; never crash on logging

    # ── Size guard ─────────────────────────────

    def _enforce_size_limit(self) -> None:
        """
        If workspace/sessions exceeds MAX_WORKSPACE_BYTES, delete the oldest
        sessions (by meta.json mtime) until we are back under limit.
        """
        if not SESSIONS_DIR.exists():
            return
        total = _dir_size(SESSIONS_DIR)
        if total <= MAX_WORKSPACE_BYTES:
            return

        sessions = sorted(
            [s for s in SESSIONS_DIR.iterdir() if s.is_dir()],
            key=_session_mtime
        )
        for oldest in sessions:
            if total <= MAX_WORKSPACE_BYTES:
                break
            sz = _dir_size(oldest)
            shutil.rmtree(oldest, ignore_errors=True)
            self.log("SYSTEM", "AUTO_PURGE", f"{oldest.name} ({sz // 1024} KB)")
            total -= sz

    # ── Session lifecycle ───────────────────────

    def begin_session(self, session_id: str, ephemeral: bool = False) -> Path:
        """
        Create or resume a workspace session.

        Parameters
        ----------
        session_id : str
            Conversation / session identifier.
        ephemeral : bool
            If True the session will be fully deleted on end_session unless
            keep_outputs=True overrides it. Defaults to False (persistent).

        Returns
        -------
        Path
            The root path of this session.
        """
        self._enforce_size_limit()

        session_path = SESSIONS_DIR / session_id
        outputs_path = session_path / "outputs"
        scratch_path = session_path / "scratch"

        outputs_path.mkdir(parents=True, exist_ok=True)
        scratch_path.mkdir(parents=True, exist_ok=True)

        meta_file = session_path / "meta.json"
        if meta_file.exists():
            # Resume existing session — update last_accessed
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            meta["last_accessed"] = datetime.now(timezone.utc).isoformat()
            meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")
            self.log(session_id, "RESUME_SESSION")
        else:
            meta = {
                "session_id": session_id,
                "ephemeral": ephemeral,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_accessed": datetime.now(timezone.utc).isoformat(),
            }
            meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")
            self.log(session_id, "BEGIN_SESSION", f"ephemeral={ephemeral}")

        return session_path

    def end_session(self, session_id: str, keep_outputs: bool = True) -> str:
        """
        Close a session.

        - scratch/ is always deleted.
        - If keep_outputs=True, outputs/ is copied to persistent/exports/<session_id>/.
        - If the session is ephemeral and keep_outputs=False, the entire session folder
          is removed; otherwise it is preserved for the next resume.

        Parameters
        ----------
        session_id : str
        keep_outputs : bool
            Default True — reflect the "infer persistent" policy.
        """
        session_path = SESSIONS_DIR / session_id
        if not session_path.exists():
            return f"Session '{session_id}' not found."

        # 1. Always purge scratch
        scratch = session_path / "scratch"
        if scratch.exists():
            shutil.rmtree(scratch, ignore_errors=True)
            scratch.mkdir()  # Re-create empty dir for next resume

        # 2. Export outputs if requested
        if keep_outputs:
            src = session_path / "outputs"
            dst = PERSISTENT_DIR / session_id
            if src.exists() and any(src.iterdir()):
                dst.mkdir(parents=True, exist_ok=True)
                for item in src.iterdir():
                    dest_item = dst / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest_item, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, dest_item)
                self.log(session_id, "EXPORT_OUTPUTS", str(dst))

        # 3. Respect ephemeral flag
        meta_file = session_path / "meta.json"
        if meta_file.exists():
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            if meta.get("ephemeral", False) and not keep_outputs:
                shutil.rmtree(session_path, ignore_errors=True)
                self.log(session_id, "END_SESSION", "DELETED (ephemeral)")
                return f"Ephemeral session '{session_id}' deleted."

        self.log(session_id, "END_SESSION", f"keep_outputs={keep_outputs}")
        return f"Session '{session_id}' closed. Outputs preserved."

    # ── Path helpers ────────────────────────────

    def get_session_path(self, session_id: str) -> Path:
        """Return the root path of a session (creates it if absent)."""
        p = SESSIONS_DIR / session_id
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_output_path(self, session_id: str, filename: str) -> Path:
        """Return a path inside the session's outputs/ folder."""
        p = SESSIONS_DIR / session_id / "outputs"
        p.mkdir(parents=True, exist_ok=True)
        return p / filename

    def get_scratch_path(self, session_id: str, filename: str) -> Path:
        """Return a path inside the session's scratch/ folder."""
        p = SESSIONS_DIR / session_id / "scratch"
        p.mkdir(parents=True, exist_ok=True)
        return p / filename

    # ── File helpers ────────────────────────────

    def write_output(self, session_id: str, filename: str, content: str) -> str:
        """Write text content to outputs/<filename> and return the absolute path."""
        out = self.get_output_path(session_id, filename)
        out.write_text(content, encoding="utf-8")
        self.log(session_id, "WRITE_OUTPUT", filename)
        return str(out)

    def list_outputs(self, session_id: str) -> list:
        """Return list of filenames in the session's outputs/ folder."""
        p = SESSIONS_DIR / session_id / "outputs"
        if not p.exists():
            return []
        return [f.name for f in p.iterdir() if f.is_file()]

    def list_persistent_exports(self, session_id: str) -> list:
        """Return list of filenames in persistent/exports/<session_id>/."""
        p = PERSISTENT_DIR / session_id
        if not p.exists():
            return []
        return [f.name for f in p.iterdir() if f.is_file()]

    def export_to_persistent(self, session_id: str, filename: str) -> str:
        """Copy a single output file to persistent/exports/<session_id>/."""
        src = SESSIONS_DIR / session_id / "outputs" / filename
        if not src.exists():
            return f"Error: '{filename}' not found in session outputs."
        dst_dir = PERSISTENT_DIR / session_id
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / filename
        shutil.copy2(src, dst)
        self.log(session_id, "EXPORT_FILE", filename)
        return str(dst)

    def cleanup_scratch(self, session_id: str) -> str:
        """Delete and recreate the scratch folder mid-task."""
        scratch = SESSIONS_DIR / session_id / "scratch"
        shutil.rmtree(scratch, ignore_errors=True)
        scratch.mkdir(parents=True)
        self.log(session_id, "CLEANUP_SCRATCH")
        return "Scratch folder cleared."

    # ── Package installation ─────────────────────

    def get_venv_python(self, session_id: str) -> Path:
        """Return the path to the venv's Python executable."""
        venv = SESSIONS_DIR / session_id / "venv"
        if os.name == "nt":
            return venv / "Scripts" / "python.exe"
        return venv / "bin" / "python"

    def get_venv_pip(self, session_id: str) -> Path:
        """Return the path to the venv's pip executable."""
        venv = SESSIONS_DIR / session_id / "venv"
        if os.name == "nt":
            return venv / "Scripts" / "pip.exe"
        return venv / "bin" / "pip"

    def ensure_venv(self, session_id: str) -> Path:
        """Create the session venv if it doesn't already exist."""
        venv = SESSIONS_DIR / session_id / "venv"
        if not venv.exists():
            subprocess.run(
                [sys.executable, "-m", "venv", str(venv)],
                check=True,
                capture_output=True
            )
            self.log(session_id, "CREATE_VENV", str(venv))
        return venv

    def install_package(self, session_id: str, package: str) -> str:
        """
        Install a pip package into the per-conversation venv.

        The venv is created on first use; subsequent calls in the same
        conversation reuse it — so install cost is paid only once.
        """
        try:
            self.ensure_venv(session_id)
            pip = self.get_venv_pip(session_id)
            result = subprocess.run(
                [str(pip), "install", package],
                capture_output=True,
                text=True,
                timeout=120
            )
            self.log(session_id, "INSTALL_PKG", package)
            combined = (result.stdout + result.stderr).strip()
            if result.returncode == 0:
                return f"Installed '{package}' successfully.\n{combined}"
            else:
                return f"Error installing '{package}':\n{combined}"
        except subprocess.TimeoutExpired:
            return f"Error: install timed out for '{package}'."
        except Exception as e:
            return f"Error: {e}"

    # ── Workspace stats ─────────────────────────

    def workspace_stats(self) -> dict:
        """Return a summary of workspace size and active sessions."""
        total_bytes = _dir_size(WORKSPACE_ROOT) if WORKSPACE_ROOT.exists() else 0
        sessions = [s.name for s in SESSIONS_DIR.iterdir() if s.is_dir()] \
            if SESSIONS_DIR.exists() else []
        return {
            "total_size_mb": round(total_bytes / (1024 * 1024), 2),
            "max_size_mb": MAX_WORKSPACE_BYTES // (1024 * 1024),
            "active_sessions": sessions,
            "persistent_exports": [p.name for p in PERSISTENT_DIR.iterdir() if p.is_dir()]
                if PERSISTENT_DIR.exists() else [],
        }


# ─────────────────────────────────────────────
# Module-level singleton
# ─────────────────────────────────────────────
workspace_manager = WorkspaceManager()
