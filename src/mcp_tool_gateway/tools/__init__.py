"""MCP tools package.

Best practice used here:
- Tool modules define *only* tool classes (no import-time side effects).
- `register_all_tools()` is called once during server startup.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Type

from ._base import BaseTool, ToolSpec
from .add import AddTool
from .ping import PingTool
from .web_search import WebSearchTool

# Single source of truth for what tools exist in this server.
_TOOL_CLASSES: tuple[Type[BaseTool], ...] = (
    PingTool,
    AddTool,
    WebSearchTool,
)

# Lazy-initialized caches (no registry.py needed)
_TOOLS: List[BaseTool] = []
_TOOL_BY_NAME: Dict[str, BaseTool] = {}


def register_all_tools() -> None:
    """Instantiate and register all tools exactly once."""
    global _TOOLS, _TOOL_BY_NAME
    if _TOOLS:
        return

    for cls in _TOOL_CLASSES:
        tool = cls()
        tool.register()
        _TOOLS.append(tool)
        _TOOL_BY_NAME[tool.spec.name] = tool


def list_tool_specs() -> list[ToolSpec]:
    register_all_tools()
    return [t.spec for t in _TOOLS]


def get_tool(tool_name: str) -> Optional[BaseTool]:
    register_all_tools()
    return _TOOL_BY_NAME.get(tool_name)
