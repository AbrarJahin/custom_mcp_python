"""MCP server instance export.

Keep this module side-effect free: importing it should *not* register tools or
start background tasks. Tool registration and session-manager startup are
handled by the FastAPI lifespan in `app.py`.
"""

from __future__ import annotations

from mcp_tool_gateway.mcp_instance import mcp

__all__ = ["mcp"]
