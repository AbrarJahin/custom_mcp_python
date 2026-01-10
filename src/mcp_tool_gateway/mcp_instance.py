from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .config import get_settings

settings = get_settings()

# Create MCP server instance. Tool registration happens when tool modules are imported.
mcp = FastMCP(settings.mcp_name)
