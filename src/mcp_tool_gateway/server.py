from __future__ import annotations

"""MCP server export.

This module exposes the FastMCP server instance as `mcp`.
Tool registration occurs when tool modules are imported.
"""

from .mcp_instance import mcp

# Import tool modules so BaseTool.register() runs at import time.
from .tools import ping as _ping  # noqa: F401
from .tools import add as _add  # noqa: F401
from .tools import web_search as _web_search  # noqa: F401

__all__ = ["mcp"]
