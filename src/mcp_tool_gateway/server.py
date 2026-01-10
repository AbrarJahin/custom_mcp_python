from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .config import get_settings

settings = get_settings()

# Create MCP server (no built-in auth wiring; we enforce auth in FastAPI middleware when enabled)
mcp = FastMCP(settings.mcp_name)


@mcp.tool()
def ping() -> str:
    """Simple connectivity test."""
    return "pong"


@mcp.tool()
def add(a: float, b: float) -> float:
    """Return a + b"""
    return a + b
