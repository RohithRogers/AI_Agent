import os
import json
import asyncio
import inspect
from typing import Dict, List, Any, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from tools.registry import registry
import rich.console

console = rich.console.Console()

class MCPManager:
    """Manages multiple MCP server connections and registers their tools."""
    
    def __init__(self):
        self.sessions: Dict[str, ClientSession] = {}
        self.server_contexts = {} # Store (read, write) context managers

    async def add_server(self, name: str, command: str, args: List[str] = None):
        """Connects to an MCP server and registers its tools."""
        try:
            params = StdioServerParameters(
                command=command, 
                args=args or [], 
                env=os.environ.copy()
            )
            
            # We use a simplified connection pattern for the CLI
            # In a more robust app, we'd manage the lifecycle better
            ctx_manager = stdio_client(params)
            read, write = await ctx_manager.__aenter__()
            session = ClientSession(read, write)
            await session.initialize()
            
            self.sessions[name] = session
            self.server_contexts[name] = ctx_manager
            
            # List tools and register them
            tools_result = await session.list_tools()
            for mcp_tool in tools_result.tools:
                self._register_mcp_as_tool(name, session, mcp_tool)
            
            console.log(f"✅ [bold green]Connected to MCP server:[/bold green] {name} ({len(tools_result.tools)} tools)")
            return True
        except Exception as e:
            console.log(f"❌ [bold red]Failed to connect to MCP server {name}:[/bold red] {e}")
            return False

    def _register_mcp_as_tool(self, server_name: str, session: ClientSession, mcp_tool):
        """Wraps an MCP tool into the standard agent registry."""
        
        # Prefixed name to avoid collisions
        tool_name = f"{server_name}_{mcp_tool.name}"
        
        async def mcp_wrapper(**kwargs):
            # Pass arguments to the MCP session
            result = await session.call_tool(mcp_tool.name, arguments=kwargs)
            # Return the content (usually text)
            if hasattr(result, "content") and result.content:
                return result.content[0].text
            return str(result)

        # Register the wrapper in the main registry
        registry.register_tool(
            name=tool_name,
            func=mcp_wrapper,
            description=f"[{server_name}] {mcp_tool.description}",
            parameters=mcp_tool.input_schema
        )

    async def close_all(self):
        """Closes all active sessions."""
        for name, session in self.sessions.items():
            await session.__aexit__(None, None, None)
        for name, ctx in self.server_contexts.items():
            await ctx.__aexit__(None, None, None)

# Global MCP Manager
mcp_manager = MCPManager()
