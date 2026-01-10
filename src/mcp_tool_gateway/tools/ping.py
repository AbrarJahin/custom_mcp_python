from __future__ import annotations

from ._base import BaseTool, ToolSpec, tool_decorator


class PingTool(BaseTool):
    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="ping",
            description="Simple connectivity test. Returns 'pong'.",
        )

    def register(self) -> None:
        @tool_decorator(name=self.spec.name, description=self.spec.description)
        def ping() -> str:
            """Simple connectivity test."""
            return "pong"
