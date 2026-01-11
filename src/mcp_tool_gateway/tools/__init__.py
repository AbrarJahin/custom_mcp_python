"""MCP tools package.

This package keeps tool *definitions* separate from tool *registration*.

- Tool modules (ping/add/web_search) define their implementation.
- Registration happens once at process startup via `register_all_tools()`.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from mcp_tool_gateway.tools._base import BaseTool, ToolSpec
from mcp_tool_gateway.tools.add import AddTool
from mcp_tool_gateway.tools.ping import PingTool
from mcp_tool_gateway.tools.web_search import WebSearchTool

_REGISTERED: bool = False
_TOOLS: List[BaseTool] = []
_TOOL_BY_NAME: Dict[str, BaseTool] = {}


def register_all_tools() -> None:
    """Register all MCP tools exactly once."""
    global _REGISTERED
    if _REGISTERED:
        return

    for cls in (PingTool, AddTool, WebSearchTool):
        tool = cls()
        tool.register()
        _TOOLS.append(tool)
        _TOOL_BY_NAME[tool.spec.name] = tool

    _REGISTERED = True


def list_tool_specs() -> list[ToolSpec]:
    register_all_tools()
    return [t.spec for t in _TOOLS]


def get_tool(tool_name: str) -> Optional[BaseTool]:
    register_all_tools()
    return _TOOL_BY_NAME.get(tool_name)
