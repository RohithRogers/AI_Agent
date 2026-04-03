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
        """Executes a tool by name with provided parameters. Supports both sync and async functions."""
        if name in self.tools:
            func = self.tools[name]["func"]
            try:
                if inspect.iscoroutinefunction(func):
                    # For async tools, we use asyncio.run to bridge to sync code
                    # Note: This works because the agent is currently synchronous
                    return asyncio.run(func(**parameters))
                return func(**parameters)
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
