import os
import subprocess
from tools.registry import tool
from tools.utils import validate_path

@tool(
    name="lint_python_code",
    description="Runs flake8 to iteratively lint a Python file and returns the warnings and errors.",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "The path to the Python file to lint."}
        },
        "required": ["file_path"]
    },
    requires_permission=True
)
def lint_python_code(file_path: str) -> str:
    """Runs flake8 on a Python file."""
    try:
        file_path = validate_path(file_path)
        if not os.path.exists(file_path):
            return f"Error: File '{file_path}' does not exist."
            
        result = subprocess.run(
            ["flake8", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        output = result.stdout.strip()
        if not output and result.returncode == 0:
            return "Linting successful: No issues found."
        elif output:
            return f"Linting issues found:\n{output}"
        else:
            return f"Error running flake8:\n{result.stderr.strip()}"
    except Exception as e:
        return f"Error linting file: {e}"

@tool(
    name="format_python_code",
    description="Runs black to automatically format a Python file.",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "The path to the Python file to format."}
        },
        "required": ["file_path"]
    },
    requires_permission=True
)
def format_python_code(file_path: str) -> str:
    """Runs black on a Python file."""
    try:
        file_path = validate_path(file_path)
        if not os.path.exists(file_path):
            return f"Error: File '{file_path}' does not exist."
            
        result = subprocess.run(
            ["black", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # black prints everything to stderr usually for logging
        output = result.stderr.strip() + "\n" + result.stdout.strip()
        
        if result.returncode == 0:
            return f"Formatting successful:\n{output.strip()}"
        else:
            return f"Error running black:\n{output.strip()}"
    except Exception as e:
        return f"Error formatting file: {e}"
