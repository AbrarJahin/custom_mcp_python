from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .auth import SimpleApiKeyVerifier
from .tools.files import read_pdf_text, read_text
from .tools.web import web_fetch, web_search_ddg

# Production-friendly defaults for Streamable HTTP:
# stateless_http=True + json_response=True
mcp = FastMCP(
    name="Tool Gateway",
    stateless_http=True,
    json_response=True,
    token_verifier=SimpleApiKeyVerifier(),
)

# -------------------------
# System tools
# -------------------------
@mcp.tool()
def system_ping() -> dict:
    """Basic health/ping tool."""
    return {"ok": True, "service": "mcp-tool-gateway"}

# -------------------------
# Web tools
# -------------------------
@mcp.tool()
async def web_fetch_tool(url: str) -> dict:
    """Fetch allowed URL and return text."""
    return await web_fetch(url)

@mcp.tool()
async def web_search_ddg_tool(query: str, max_results: int = 5) -> dict:
    """DuckDuckGo search and return top results."""
    return {"query": query, "results": await web_search_ddg(query, max_results=max_results)}

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
