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
    """Abstract base class that every tool must implement.

    Each tool provides:
      - a stable name
      - a human-friendly description
      - a register() method that registers the tool with the FastMCP instance
    """

    @property
    @abstractmethod
    def spec(self) -> ToolSpec:  # pragma: no cover
        raise NotImplementedError

    @abstractmethod
    def register(self) -> None:  # pragma: no cover
        """Register tool functions with the MCP server."""
        raise NotImplementedError


def tool_decorator(*, name: str | None = None, description: str | None = None):
    """Small helper around mcp.tool().

    We keep this helper so tools don't need to import `mcp` directly.
    """
    # FastMCP supports decorator usage; name/description may be honored depending on SDK version.
    # We still set function docstrings for clients that read them.
    return mcp.tool(name=name, description=description)  # type: ignore[arg-type]
