from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .auth import SimpleApiKeyVerifier
from .config import settings
from .tools.files import read_pdf_text, read_text
from .tools.web import web_fetch, web_search_ddg


# Stateless + JSON is recommended for scalable Streamable HTTP deployments. citeturn4view0
mcp = FastMCP(
    name="Detoura Tool Gateway",
    stateless_http=True,
    json_response=True,
    token_verifier=SimpleApiKeyVerifier(),
)


@mcp.tool()
def system_ping() -> dict:
    """Health check tool."""
    return {"ok": True, "service": "mcp-tool-gateway"}


# -------------------------
# Web tools
# -------------------------
@mcp.tool()
async def web_fetch_tool(url: str) -> dict:
    """Fetch a URL (allowlisted domains, size/time limits)."""
    return await web_fetch(url)


@mcp.tool()
async def web_search_ddg_tool(query: str, max_results: int = 5) -> list[dict]:
    """Search the web using DuckDuckGo and return top results."""
    return await web_search_ddg(query, max_results=max_results)


# -------------------------
# File tools
# -------------------------
@mcp.tool()
def files_read_text_tool(path: str, max_chars: int = 50_000) -> dict:
    """Read a text file under FILES_BASE_DIR."""
    return read_text(path, max_chars=max_chars)


@mcp.tool()
def files_read_pdf_text_tool(path: str, max_pages: int = 10, max_chars: int = 80_000) -> dict:
    """Extract basic text from a PDF under FILES_BASE_DIR."""
    return read_pdf_text(path, max_pages=max_pages, max_chars=max_chars)
