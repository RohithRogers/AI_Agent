import sys
import io
import os
from tools.registry import tool
from tools.utils import get_active_session, resolve_workspace_path

# Persistent state for the REPL — survives across tool calls in same process
repl_globals = {}

def _prepare_repl_globals() -> dict:
    """
    Keep repl_globals up to date with the current workspace scratch path so
    code executed inside the REPL can safely write temp files there.
    """
    session_id = get_active_session()
    if session_id:
        scratch_str = resolve_workspace_path(".", sub="scratch")
        repl_globals["SCRATCH_DIR"] = scratch_str
        repl_globals["__file__"] = os.path.join(scratch_str, "<repl>")
    else:
        repl_globals.pop("SCRATCH_DIR", None)
    return repl_globals


@tool(
    name="execute_python",
    description=(
        "Executes arbitrary Python code in a persistent REPL session and returns "
        "its stdout output. The variable SCRATCH_DIR is automatically set in the "
        "execution context to the current workspace scratch folder — use it when "
        "writing any temporary files so they are auto-cleaned up."
    ),
    parameters={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "The Python code to execute."}
        },
        "required": ["code"]
    },
    requires_permission=True
)
def execute_python_code(code: str) -> str:
    """Executes Python code and returns output."""
    globals_ctx = _prepare_repl_globals()

    # Capture stdout
    old_stdout = sys.stdout
    new_stdout = io.StringIO()
    sys.stdout = new_stdout

    try:
        try:
            result = eval(code, globals_ctx)
            if result is not None:
                print(result)
        except SyntaxError:
            exec(code, globals_ctx)

        output = new_stdout.getvalue()
        return output if output else "Executed successfully (no output)."
    except Exception as e:
        return f"Execution Error: {e}"
    finally:
        sys.stdout = old_stdout
