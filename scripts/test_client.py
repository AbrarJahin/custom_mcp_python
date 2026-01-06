from __future__ import annotations

import asyncio
import os

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


MCP_URL = os.getenv("MCP_URL", "http://localhost:8000/mcp")
API_KEY = os.getenv("MCP_API_KEY", "dev-key-1")


async def main() -> None:
    http_client = httpx.AsyncClient(
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=20.0,
        follow_redirects=True,
    )

    async with streamable_http_client(MCP_URL, http_client=http_client) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Tools:", [t.name for t in tools.tools])

            res = await session.call_tool("system_ping", arguments={})
            print("Ping:", res.structuredContent)

            res = await session.call_tool(
                "files_read_text_tool",
                arguments={"path": "hello.txt"},
            )
            print("Read file:", res.structuredContent)

            res = await session.call_tool(
                "web_search_ddg_tool",
                arguments={"query": "Model Context Protocol streamable HTTP", "max_results": 3},
            )
            print("Search:", res.structuredContent)


if __name__ == "__main__":
    asyncio.run(main())
