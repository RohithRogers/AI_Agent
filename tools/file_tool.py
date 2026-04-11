import os
from tools.registry import tool
from tools.utils import validate_path

@tool(
    name="read_file",
    description="Reads the content of a file at the specified path.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "The full path to the file."}
        },
        "required": ["path"]
    },
    requires_permission=True
)
def read_file(path):
    try:
        path = validate_path(path)
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
    },
    requires_permission=True
)
def write_file(path, content):
    try:
        path = validate_path(path)
        with open(path, 'w') as f:
            f.write(content)
        return f"Successfully wrote to file '{path}'."
    except Exception as e:
        return f"Error writing to file: {str(e)}"

@tool(
    name="list_directory",
    description="Lists the contents of a directory.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "The path to the directory."}
        },
        "required": ["path"]
    },
    requires_permission=True
)
def list_directory(path):
    try:
        path = validate_path(path)
        return str(os.listdir(path))
    except Exception as e:
        return f"Error listing directory: {str(e)}"

@tool(
    name="create_directory",
    description="Creates a new directory at the specified path.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "The full path to the directory to create."}
        },
        "required": ["path"]
    },
    requires_permission=True
)
def create_directory(path):
    """Creates a new directory."""
    try:
        path = validate_path(path)
        os.makedirs(path, exist_ok=True)
        return f"Directory '{path}' created successfully."
    except Exception as e:
        return f"Error creating directory: {str(e)}"

@tool(
    name="delete_file",
    description="Deletes a file at the specified path.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "The full path to the file to delete."}
        },
        "required": ["path"]
    },
    requires_permission=True
)
def delete_file(path):
    """Deletes a file."""
    try:
        path = validate_path(path)
        os.remove(path)
        return f"File '{path}' deleted successfully."
    except Exception as e:
        return f"Error deleting file: {str(e)}"

# Edit file with show differences
@tool(
    name="edit_file",
    description="Edits a file at the specified path.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "The full path to the file."},
            "content": {"type": "string", "description": "The content to write to the file."}
        },
        "required": ["path", "content"]
    },
    requires_permission=True
)
def edit_file(path, content):
    try:
        path = validate_path(path)
        with open(path, 'w') as f:
            f.write(content)
        return f"Successfully edited file '{path}'."
    except Exception as e:
        return f"Error editing file: {str(e)}"

