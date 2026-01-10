from __future__ import annotations

from typing import Dict

from .base import BaseTool, ToolSpec


_TOOL_REGISTRY: Dict[str, BaseTool] = {}


def register_tool(tool: BaseTool) -> None:
    spec = tool.spec
    _TOOL_REGISTRY[spec.name] = tool


def list_tool_specs() -> list[ToolSpec]:
    return [t.spec for t in _TOOL_REGISTRY.values()]


def get_tool(tool_name: str) -> BaseTool | None:
    return _TOOL_REGISTRY.get(tool_name)
