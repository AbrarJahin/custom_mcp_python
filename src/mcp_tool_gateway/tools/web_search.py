from __future__ import annotations

from typing import Any

from mcp_tool_gateway.tools._base import BaseTool, ToolSpec, tool_decorator
from mcp_tool_gateway.services.web_service import web_search_ddg


class WebSearchTool(BaseTool):
    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="web_search",
            description="Search the web using DuckDuckGo (duckduckgo-async-search).",
        )

    def register(self) -> None:
        @tool_decorator(name=self.spec.name, description=self.spec.description)
        async def web_search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
            """Search the web using DuckDuckGo via duckduckgo-async-search.

            Args:
                query: Search query text.
                max_results: Number of results to return (clamped to a safe range).

            Returns:
                List of dict results with: rank, title, url, snippet.
            """
            return await web_search_ddg(query=query, max_results=max_results)
