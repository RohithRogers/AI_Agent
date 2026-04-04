import sys
import io
from tools.registry import tool

# Persistent state for the REPL
repl_globals = {}

@tool(
    name="execute_python",
    description="Executes arbitrary Python code in a persistent session and returns its output (stdout).",
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
    global repl_globals
    
    # Capture stdout
    old_stdout = sys.stdout
    new_stdout = io.StringIO()
    sys.stdout = new_stdout
    
    try:
        # We try to eval if it's an expression for direct return
        # But for logic snippets we use exec
        try:
            # First try if it's a simple expression that can be printed
            result = eval(code, repl_globals)
            if result is not None:
                print(result)
        except SyntaxError:
            # Otherwise execute it as a statement/block
            exec(code, repl_globals)
        
        output = new_stdout.getvalue()
        return output if output else "Executed successfully (no output)."
    except Exception as e:
        return f"Execution Error: {e}"
    finally:
        sys.stdout = old_stdout
