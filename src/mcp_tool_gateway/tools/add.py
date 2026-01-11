from __future__ import annotations

from mcp_tool_gateway.tools._base import BaseTool, ToolSpec, tool_decorator


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
            """Return a + b."""
            return a + b
