from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx
from duckduckgo_async_search import top_n_result

from mcp_tool_gateway.config import settings


def _url_allowed(url: str) -> bool:
    """Return True if URL is allowed to be fetched.

    Best-practice note:
    - In production, consider enabling an allowlist.
    - For this project, **all http/https URLs are allowed** per requirements.
    """
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.hostname)


async def web_fetch(
    url: str,
    *,
    timeout_s: float | None = None,
    max_bytes: int | None = None,
    max_chars: int | None = None,
) -> dict[str, Any]:
    """Fetch a URL (basic scheme validation + size cap + timeout).

    Args:
        url: The URL to fetch.
        timeout_s: Request timeout seconds. Defaults from env.
        max_bytes: Maximum bytes to download. Defaults from env.
        max_chars: Maximum chars returned in `text`. Defaults from env.

    Returns:
        Dict with url, status_code, text (truncated), headers (subset).
    """
    if not _url_allowed(url):
        return {"url": url, "status_code": None, "text": "", "error": "URL not allowed"}

    timeout_s = float(timeout_s or settings.web_fetch_timeout_s)
    max_bytes = int(max_bytes or settings.web_max_bytes)
    max_chars = int(max_chars or 8000)

    headers = {"User-Agent": settings.web_user_agent}
    async with httpx.AsyncClient(follow_redirects=True, headers=headers, timeout=timeout_s) as client:
        r = await client.get(url)
        content = r.content[:max_bytes]
        # Best-effort decode
        try:
            text = content.decode(r.encoding or "utf-8", errors="replace")
        except Exception:
            text = content.decode("utf-8", errors="replace")
        text = text[:max_chars]
        return {
            "url": url,
            "status_code": r.status_code,
            "text": text,
            "headers": {
                "content-type": r.headers.get("content-type", ""),
                "content-length": r.headers.get("content-length", ""),
            },
        }


async def web_search_ddg(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """DuckDuckGo web search via `duckduckgo-async-search`.

    Returns list of dicts: rank, title, url, snippet.
    """
    # Clamp for safety
    max_results = max(1, min(int(max_results), 20))
    results = await top_n_result(query, max_results)

    out: list[dict[str, Any]] = []
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
