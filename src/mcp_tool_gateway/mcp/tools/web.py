from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx
from duckduckgo_async_search import top_n_result

from ...core.config import settings

_domain_re = re.compile(r"^[a-z0-9.-]+$", re.I)


def _domain_allowed(host: str) -> bool:
    host = host.lower().strip(".")
    if not host or not _domain_re.match(host):
        return False
    allowed = settings.allowed_domains()
    if not allowed:
        return False
    return any(host == d or host.endswith("." + d) for d in allowed)


def _is_allowed_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    if not parsed.hostname:
        return False
    return _domain_allowed(parsed.hostname)


async def web_fetch(url: str) -> dict:
    """Fetch a URL (allowlist + size cap + timeout)."""
    if not _is_allowed_url(url):
        raise ValueError(f"URL not allowed by WEB_ALLOWED_DOMAINS: {url}")

    timeout = settings.web_fetch_timeout_s
    max_bytes = settings.web_max_bytes

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        r = await client.get(url, headers={"User-Agent": "mcp-tool-gateway/0.1"})
        r.raise_for_status()

        # cap bytes
        content = r.content[:max_bytes]
        text = content.decode(r.encoding or "utf-8", errors="replace")

    return {
        "url": str(r.url),
        "status_code": r.status_code,
        "bytes": len(content),
        "text": text,
        "content_type": r.headers.get("content-type", ""),
    }


async def web_search_ddg(query: str, max_results: int = 5) -> list[dict]:
    """DuckDuckGo search via duckduckgo-async-search."""
    max_results = max(1, min(int(max_results), 10))
    results = await top_n_result(query, n=max_results)

    out: list[dict] = []
    for i, item in enumerate(results, start=1):
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "rank": i,
                "title": item.get("title") or "",
                "url": item.get("href") or item.get("url") or "",
                "snippet": item.get("body") or item.get("snippet") or "",
            }
        )
    return out


def register(mcp) -> None:
    """Register web tools on the given FastMCP instance."""

    @mcp.tool(name="web.search_ddg")
    async def tool_web_search_ddg(query: str, max_results: int = 5) -> list[dict]:
        """Search DuckDuckGo (async) and return a ranked list of results.

        Uses duckduckgo-async-search internally.
        """
        return await web_search_ddg(query=query, max_results=max_results)

    @mcp.tool(name="web.fetch")
    async def tool_web_fetch(url: str) -> dict:
        """Fetch a URL with allowlist + size cap + timeout."""
        return await web_fetch(url=url)
