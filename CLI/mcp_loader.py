import os
from tools.mcp_registry import mcp_manager

async def _load_mcp_from_env():
    """Initializes MCP servers listed in the environment."""
    server_list = os.getenv("MCP_SERVERS", "").split(",")
    for s in server_list:
        name = s.strip()
        if not name: continue
        cmd = os.getenv(f"MCP_SERVER_{name.upper()}_COMMAND")
        if cmd:
            await mcp_manager.add_server(name, cmd)
