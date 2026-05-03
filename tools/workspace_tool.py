"""
workspace_tool.py
-----------------
Registers all workspace-related tools so the agent can call them directly.

Tools exposed
-------------
  workspace_begin           - Start or resume a session
  workspace_end             - Close a session (default: keep outputs)
  workspace_write_output    - Write text/content into outputs/
  workspace_install_package - Install pip package into session venv
  workspace_list_outputs    - List artefacts in current session outputs/
  workspace_export_file     - Copy a single output to persistent/exports/
  workspace_cleanup_scratch - Wipe scratch/ mid-task without closing session
  workspace_stats           - Report total disk usage and session list
"""

from tools.registry import tool
from tools.workspace_manager import workspace_manager


# ── Begin / End ────────────────────────────────────────────────────────────────

@tool(
    name="workspace_begin",
    description=(
        "Start or resume an agent workspace session for the given conversation. "
        "Call this at the start of any task that will produce files or need isolated "
        "package installs. Returns the session's root path."
    ),
    parameters={
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "Unique identifier for the conversation/session (e.g. the conversation ID)."
            },
            "ephemeral": {
                "type": "boolean",
                "description": (
                    "If true the session folder is deleted when ended without keeping outputs. "
                    "Default false — outputs are kept across turns."
                )
            }
        },
        "required": ["session_id"]
    },
    requires_permission=False
)
def workspace_begin(session_id: str, ephemeral: bool = False) -> str:
    path = workspace_manager.begin_session(session_id, ephemeral=ephemeral)
    return f"Workspace session '{session_id}' ready at: {path}"


@tool(
    name="workspace_end",
    description=(
        "Close the workspace session. Scratch files are always deleted. "
        "If keep_outputs is True (the default), outputs are also copied to the "
        "persistent exports directory before the session closes."
    ),
    parameters={
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "The session identifier to close."
            },
            "keep_outputs": {
                "type": "boolean",
                "description": "Copy outputs to persistent/exports when closing. Default true."
            }
        },
        "required": ["session_id"]
    },
    requires_permission=False
)
def workspace_end(session_id: str, keep_outputs: bool = True) -> str:
    return workspace_manager.end_session(session_id, keep_outputs=keep_outputs)


# ── File I/O ───────────────────────────────────────────────────────────────────

@tool(
    name="workspace_write_output",
    description=(
        "Write text content to a named file inside the session's outputs/ folder. "
        "Use this for any file the user should receive (reports, CSVs, markdown, etc.). "
        "Returns the absolute path of the saved file."
    ),
    parameters={
        "type": "object",
        "properties": {
            "session_id": {"type": "string", "description": "The session identifier."},
            "filename":   {"type": "string", "description": "Name of the file, e.g. 'report.md'."},
            "content":    {"type": "string", "description": "Text content to write."}
        },
        "required": ["session_id", "filename", "content"]
    },
    requires_permission=True
)
def workspace_write_output(session_id: str, filename: str, content: str) -> str:
    return workspace_manager.write_output(session_id, filename, content)


@tool(
    name="workspace_list_outputs",
    description="List all files currently in the session's outputs/ folder.",
    parameters={
        "type": "object",
        "properties": {
            "session_id": {"type": "string", "description": "The session identifier."}
        },
        "required": ["session_id"]
    },
    requires_permission=False
)
def workspace_list_outputs(session_id: str) -> str:
    files = workspace_manager.list_outputs(session_id)
    if not files:
        return "No output files found in this session."
    return "Session outputs:\n" + "\n".join(f"  • {f}" for f in files)


@tool(
    name="workspace_export_file",
    description=(
        "Copy a specific file from the session's outputs/ to the persistent exports folder "
        "so it survives beyond this session. Use when the user explicitly wants to keep a file."
    ),
    parameters={
        "type": "object",
        "properties": {
            "session_id": {"type": "string", "description": "The session identifier."},
            "filename":   {"type": "string", "description": "Filename to export (must exist in outputs/)."}
        },
        "required": ["session_id", "filename"]
    },
    requires_permission=True
)
def workspace_export_file(session_id: str, filename: str) -> str:
    result = workspace_manager.export_to_persistent(session_id, filename)
    return f"Exported to: {result}"


# ── Scratch cleanup ────────────────────────────────────────────────────────────

@tool(
    name="workspace_cleanup_scratch",
    description=(
        "Delete all files in the session's scratch/ folder without closing the session. "
        "Use after a mid-task computation to free up disk space."
    ),
    parameters={
        "type": "object",
        "properties": {
            "session_id": {"type": "string", "description": "The session identifier."}
        },
        "required": ["session_id"]
    },
    requires_permission=False
)
def workspace_cleanup_scratch(session_id: str) -> str:
    return workspace_manager.cleanup_scratch(session_id)


# ── Package install ────────────────────────────────────────────────────────────

@tool(
    name="workspace_install_package",
    description=(
        "Install a Python package via pip into the session's isolated virtual environment. "
        "The venv is created on first call and reused for the rest of the conversation, "
        "so subsequent installs are fast. Use this instead of installing globally."
    ),
    parameters={
        "type": "object",
        "properties": {
            "session_id": {"type": "string", "description": "The session identifier."},
            "package":    {"type": "string", "description": "Package name (and optional version), e.g. 'requests==2.31.0'."}
        },
        "required": ["session_id", "package"]
    },
    requires_permission=True
)
def workspace_install_package(session_id: str, package: str) -> str:
    return workspace_manager.install_package(session_id, package)


# ── Stats ──────────────────────────────────────────────────────────────────────

@tool(
    name="workspace_stats",
    description=(
        "Return current workspace disk usage, the 100 MB cap, and a list of active "
        "sessions and persistent exports."
    ),
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    },
    requires_permission=False
)
def workspace_stats() -> str:
    stats = workspace_manager.workspace_stats()
    lines = [
        f"Workspace usage : {stats['total_size_mb']} MB / {stats['max_size_mb']} MB",
        f"Active sessions : {', '.join(stats['active_sessions']) or 'none'}",
        f"Persistent exports: {', '.join(stats['persistent_exports']) or 'none'}",
    ]
    return "\n".join(lines)
