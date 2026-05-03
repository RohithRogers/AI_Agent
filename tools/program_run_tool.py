from tools.registry import tool
from tools.terminal_manager import terminal_manager
import os
from tools.utils import validate_path, get_active_session, resolve_workspace_path
from tools.workspace_manager import SESSIONS_DIR


def _get_scratch_cwd() -> str | None:
    """
    Return the absolute path to the current session's scratch folder,
    or None if no workspace session is active.
    """
    session_id = get_active_session()
    if not session_id:
        return None
    scratch = SESSIONS_DIR / session_id / "scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    return str(scratch)


@tool(
    name="program_run",
    description=(
        "Runs a program (Python, C, C++). "
        "Compiled binaries and temp artefacts are placed in the workspace "
        "scratch folder so they are auto-cleaned after the session ends."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path":     {"type": "string", "description": "The path to the source file."},
            "language": {"type": "string", "description": "The language (python, c, cpp)."}
        },
        "required": ["path", "language"]
    },
    requires_permission=True
)
def program_run(path, language):
    try:
        path = validate_path(path)
        if not os.path.exists(path):
            yield f"Error: File '{path}' not found."
            return

        scratch = _get_scratch_cwd()
        out_bin = os.path.join(scratch, "temp_app.exe") if scratch else "temp_app.exe"

        if language == "python":
            cmd = f"python \"{path}\""
        elif language == "c":
            cmd = f"gcc \"{path}\" -o \"{out_bin}\"; if ($?) {{ & \"{out_bin}\" }}"
        elif language == "cpp":
            cmd = f"g++ \"{path}\" -o \"{out_bin}\"; if ($?) {{ & \"{out_bin}\" }}"
        else:
            yield f"Error: Language '{language}' is not supported."
            return

        # Run from scratch dir so relative file I/O lands in a safe place
        yield from terminal_manager.execute_stream(cmd, cwd=scratch)
    except Exception as e:
        yield f"Execution error: {e}"


@tool(
    name="command_executor",
    description=(
        "Executes a PowerShell command in the persistent terminal session. "
        "When a workspace session is active, commands run from the scratch folder."
    ),
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "The PowerShell command to execute."}
        },
        "required": ["command"]
    },
    requires_permission=True
)
def command_executor(command):
    scratch = _get_scratch_cwd()
    yield from terminal_manager.execute_stream(command, cwd=scratch)