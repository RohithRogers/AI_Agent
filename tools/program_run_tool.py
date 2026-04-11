from tools.registry import tool
from tools.terminal_manager import terminal_manager
import os
from tools.utils import validate_path

@tool(
    name="program_run",
    description="Runs a program (Python, C, C++).",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "The path to the source file."},
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
            return f"Error: File '{path}' not found."
        
        if language == "python":
            cmd = f"python {path}"
        elif language == "c":
            cmd = f"gcc {path} -o temp_app.exe; if ($?) {{ ./temp_app.exe }}"
        elif language == "cpp":
            cmd = f"g++ {path} -o temp_app.exe; if ($?) {{ ./temp_app.exe }}"
        else:
            return f"Error: Language '{language}' is not supported."
        
        # Yield each line of output as it arrives
        yield from terminal_manager.execute_stream(cmd)
    except Exception as e:
        yield f"Execution error: {e}"


@tool(
    name="command_executor",
    description="Executes a powershell command in the persistent session.",
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "The command to execute."}
        },
        "required": ["command"]
    },
    requires_permission=True
)
def command_executor(command):
    yield from terminal_manager.execute_stream(command)