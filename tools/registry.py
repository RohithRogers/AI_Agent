import json
import inspect
import asyncio

class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def register_tool(self, name, func, description, parameters, requires_permission=False):
        """Registers a Python function as a tool for the agent."""
        self.tools[name] = {
            "name": name,
            "func": func,
            "description": description,
            "parameters": parameters,
            "requires_permission": requires_permission,
        }

    def get_tool_schemas(self):
        """Returns a list of JSON schemas for all registered tools."""
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"]
            } for tool in self.tools.values()
        ]

    def execute_tool(self, name, parameters):
        """Executes a tool by name. Returns result or a generator for streaming output."""
        if name in self.tools:
            tool_info = self.tools[name]
            func = tool_info["func"]
            try:
                # Handle async functions
                if inspect.iscoroutinefunction(func):
                    return asyncio.run(func(**parameters))
                
                # Execute the function
                result = func(**parameters)
                
                # Return direct result or generator
                return result
            except Exception as e:
                return f"Error executing tool '{name}': {str(e)}"
        return f"Error: Tool '{name}' not found."

# Global registry instance
registry = ToolRegistry()

def tool(name, description, parameters, requires_permission=False):
    """Decorator to easily register tools."""
    def decorator(func):
        registry.register_tool(name, func, description, parameters, requires_permission)
        return func
    return decorator
