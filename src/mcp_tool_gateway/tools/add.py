from __future__ import annotations

from .base import BaseTool, ToolSpec, tool_decorator
from .registry import register_tool


class AddTool(BaseTool):
    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="add",
            description="Return a + b (float).",
        )

    def register(self) -> None:
        @tool_decorator(name=self.spec.name, description=self.spec.description)
        def add(a: float, b: float) -> float:
            """Return a + b"""
            return a + b


_tool = AddTool()
register_tool(_tool)
_tool.register()
