import os
from config import BASE_DIR

def validate_path(path):
    """
    Ensures that the provided path is within the project's BASE_DIR.
    Prevents directory traversal attacks.
    """
    abs_path = os.path.abspath(path)
    if not abs_path.startswith(os.path.abspath(BASE_DIR)):
        raise PermissionError(f"Access denied: Path '{path}' is outside the permitted workspace.")
    return abs_path
