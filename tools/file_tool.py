import os
from tools.registry import tool

@tool(
    name="read_file",
    description="Reads the content of a file at the specified path.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "The full path to the file."}
        },
        "required": ["path"]
    }
)
def read_file(path):
    try:
        if not os.path.exists(path):
            return f"Error: File '{path}' does not exist."
        with open(path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

@tool(
    name="write_file",
    description="Writes content to a file at the specified path.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "The full path to the file."},
            "content": {"type": "string", "description": "The content to write to the file."}
        },
        "required": ["path", "content"]
    }
)
def write_file(path, content):
    try:
        with open(path, 'w') as f:
            f.write(content)
        return f"Successfully wrote to file '{path}'."
    except Exception as e:
        return f"Error writing to file: {str(e)}"

