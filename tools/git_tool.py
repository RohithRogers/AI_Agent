import subprocess
from tools.registry import tool

@tool(
    name="git_status",
    description="Returns the current status of the git repository.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "The directory path (default is project root)."}
        }
    }
)
def git_status(path: str = ".") -> str:
    """Gets the status of the current git repo."""
    try:
        result = subprocess.check_output(["git", "status"], cwd=path, stderr=subprocess.STDOUT, text=True)
        return result
    except subprocess.CalledProcessError as e:
        return f"Error: {e.output}"
    except Exception as e:
        return f"System Error: {e}"

@tool(
    name="git_diff",
    description="Returns the diff between current staging area and head.",
    parameters={
        "type": "object",
        "properties": {
            "staged": {"type": "boolean", "description": "Pass true to see staged changes."}
        }
    }
)
def git_diff(staged: bool = False) -> str:
    """Gets the diff for the current repo."""
    try:
        cmd = ["git", "diff"]
        if staged: cmd.append("--cached")
        result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
        return result if result else "No changes detected."
    except subprocess.CalledProcessError as e:
        return f"Error: {e.output}"

@tool(
    name="git_log",
    description="Returns the recent git commit history.",
    parameters={
        "type": "object",
        "properties": {
            "n": {"type": "integer", "description": "Number of recent commits to show."}
        }
    }
)
def git_log(n: int = 5) -> str:
    """Gets the recent git commit history."""
    try:
        result = subprocess.check_output(["git", "log", f"-n {n}", "--oneline"], stderr=subprocess.STDOUT, text=True)
        return result
    except subprocess.CalledProcessError as e:
        return f"Error: {e.output}"
