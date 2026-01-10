from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..mcp_instance import mcp


@dataclass(frozen=True)
class ToolSpec:
    """Metadata for an MCP tool (for discovery endpoints)."""

    name: str
    description: str


class BaseTool(ABC):
    """Base class for MCP tools.

    Each tool:
      - exposes a ToolSpec via `spec`
      - registers one or more MCP tool functions via `register()`
    """

    @property
    @abstractmethod
    def spec(self) -> ToolSpec:  # pragma: no cover
        raise NotImplementedError

    @abstractmethod
    def register(self) -> None:  # pragma: no cover
        """Register tool functions with the shared FastMCP instance."""
        raise NotImplementedError


def tool_decorator(*, name: str, description: str):
    """Thin wrapper around `mcp.tool()`.

    Keeping this helper avoids importing `mcp` directly in every tool module.
    """
    # FastMCP supports decorator usage; name/description are used for discovery.
    return mcp.tool(name=name, description=description)  # type: ignore[arg-type]
