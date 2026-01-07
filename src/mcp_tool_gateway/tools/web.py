from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx
from duckduckgo_async_search import top_n_result

from ..config import settings

_domain_re = re.compile(r"^[a-z0-9.-]+$", re.I)


def _is_subdomain(host: str, base: str) -> bool:
    host = host.lower().strip(".")
    base = base.lower().strip(".")
    return host == base or host.endswith("." + base)


def _domain_allowed(host: str) -> bool:
    host = host.lower().strip(".")
    if not host or not _domain_re.match(host):
        return False

    allowed = settings.allowed_domains()
    # If user configured "*" or left it empty, treat as allow-all (optional).
    if not allowed:
        return True
    if "*" in allowed:
        return True

    return any(_is_subdomain(host, d) for d in allowed)


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


async def web_fetch(url: str, max_chars: int = 50_000) -> dict:
    """Fetch a URL (allowlisted domains). Returns text truncated to max_chars."""
    max_chars = max(500, min(int(max_chars), 200_000))

    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http/https URLs are allowed")
    if not _domain_allowed(host):
        raise PermissionError(f"Domain not allowed: {host}")

    timeout = httpx.Timeout(settings.web_fetch_timeout_s)
    headers = {"User-Agent": "mcp-tool-gateway/0.1"}

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        r = await client.get(url)
        r.raise_for_status()

        content = r.content
        if len(content) > settings.web_max_bytes:
            content = content[: settings.web_max_bytes]

        # Best-effort decode
        try:
            text = content.decode(r.encoding or "utf-8", errors="replace")
        except Exception:
            text = content.decode("utf-8", errors="replace")

        if len(text) > max_chars:
            text = text[:max_chars]

        return {
            "url": str(r.url),
            "status_code": r.status_code,
            "content_type": r.headers.get("content-type", ""),
            "text": text,
            "bytes_read": len(content),
        }
