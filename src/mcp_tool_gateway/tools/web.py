from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx
from duckduckgo_async_search import top_n_result

from ..config import settings


_domain_re = re.compile(r"^[a-z0-9.-]+$")


def _is_allowed_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    if not host or not _domain_re.match(host):
        return False

    # allow exact host or subdomain of allowed domains
    allowed = settings.allowed_domains()
    return any(host == d or host.endswith("." + d) for d in allowed)


async def web_fetch(url: str) -> dict:
    """Fetch a URL with strict safety limits.

    Returns JSON-friendly dict with {url, status_code, headers_subset, text}.
    """
    if not _is_allowed_url(url):
        raise ValueError(f"URL host not allowed: {url}")

    timeout = httpx.Timeout(settings.web_fetch_timeout_s)
    limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)

    async with httpx.AsyncClient(timeout=timeout, limits=limits, follow_redirects=True) as client:
        r = await client.get(url, headers={"User-Agent": "mcp-tool-gateway/0.1"})
        content = r.content[: settings.web_max_bytes]
        text = content.decode(errors="replace")
        return {
            "url": str(r.url),
            "status_code": r.status_code,
            "content_type": r.headers.get("content-type", ""),
            "text": text,
        }


async def web_search_ddg(query: str, max_results: int = 5) -> list[dict]:
    """DuckDuckGo search via duckduckgo-async-search.

    Returns list[{title,url,snippet,rank}]
    """
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
