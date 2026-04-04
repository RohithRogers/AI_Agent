import sys
import os

# Add the project root to sys.path so we can use absolute imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Ensure tools are imported so they register themselves
from tools import (
    time_tool, 
    file_tool, 
    program_run_tool, 
    voice_handler, 
    python_repl_tool, 
    git_tool, 
    doc_tool, 
    browser_tool
)
from CLI.commands import main

if __name__ == "__main__":
    main()
