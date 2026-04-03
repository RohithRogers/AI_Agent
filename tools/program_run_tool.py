from tools.registry import tool
import subprocess
import os

@tool(
    name="run_program",
    description="Runs a program at the specified path.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "The full path to the program."},
            "language":{"type":"string","description":"The language of the program."}
        },
        "required": ["path","language"]
    },
    requires_permission=True
)
def run_program(path,language):
    try:
        if not os.path.exists(path):
            return f"Error: Program '{path}' does not exist."
        if language == "python":
            result = subprocess.run(["python", path],capture_output=True,text=True)
            return result.stdout
        elif language == "c":
            compiled = subprocess.run(["gcc", path],capture_output=True,text=True)
            result = subprocess.run(["./a.exe"],capture_output=True,text=True)
            return result.stdout
        elif language == "cpp":
            compiled = subprocess.run(["g++", path],capture_output=True,text=True)
            result = subprocess.run(["./a.exe"],capture_output=True,text=True)
            return result.stdout
        else:
            return f"Error: Language '{language}' is not supported."
    except Exception as e:
        return f"Error running program: {str(e)}"


@tool(
    name="command_executor",
    description="Executes a command in the terminal.",
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
    try:
        result = subprocess.run(command,shell=True,capture_output=True,text=True)
        return result.stdout
    except Exception as e:
        return f"Error executing command: {str(e)}"