import json

class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def register_tool(self, name, func, description, parameters):
        """Registers a Python function as a tool for the agent."""
        self.tools[name] = {
            "name": name,
            "func": func,
            "description": description,
            "parameters": parameters,
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
        """Executes a tool by name with provided parameters."""
        if name in self.tools:
            return self.tools[name]["func"](**parameters)
        return f"Error: Tool '{name}' not found."

# Global registry instance
registry = ToolRegistry()

def tool(name, description, parameters):
    """Decorator to easily register tools."""
    def decorator(func):
        registry.register_tool(name, func, description, parameters)
        return func
    return decorator
