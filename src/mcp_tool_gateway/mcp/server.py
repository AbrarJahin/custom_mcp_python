from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..core.config import get_settings
from .tools import web as web_tools
from .tools import files as file_tools

settings = get_settings()

# Create MCP server instance
mcp = FastMCP(settings.mcp_name)

# Register built-in sample tools (kept from original project)
@mcp.tool()
def ping() -> str:
    """Simple connectivity test."""
    return "pong"

@mcp.tool()
def add(a: float, b: float) -> float:
    """Return a + b"""
    return a + b

# Register custom tool modules
web_tools.register(mcp)
file_tools.register(mcp)
