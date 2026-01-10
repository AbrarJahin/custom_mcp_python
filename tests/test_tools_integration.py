from __future__ import annotations

import asyncio
import pytest

from mcp_tool_gateway.tools.ping import PingTool
from mcp_tool_gateway.tools.add import AddTool
from mcp_tool_gateway.tools.web_search import WebSearchTool


# -------------------------
# Helper: retry for network
# -------------------------
async def _retry_async(fn, attempts: int = 3, delay_s: float = 1.0):
    last_exc = None
    for i in range(attempts):
        try:
            return await fn()
        except Exception as e:  # noqa: BLE001 - want to retry on network errors
            last_exc = e
            if i < attempts - 1:
                await asyncio.sleep(delay_s)
    raise last_exc  # type: ignore[misc]


# -------------------------
# PING (sync tool)
# -------------------------
@pytest.mark.integration
@pytest.mark.asyncio
async def test_ping_run_async():
    t = PingTool()
    assert await t.run() == "pong"


@pytest.mark.integration
def test_ping_run_sync():
    t = PingTool()
    assert t.run_sync() == "pong"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ping_run_stream():
    t = PingTool()
    out = []
    async for item in t.run_stream():
        out.append(item)

    # Non-streaming tool yields exactly one item via _base.py coercion
    assert out == ["pong"]


# -------------------------
# ADD (sync tool)
# -------------------------
@pytest.mark.integration
@pytest.mark.asyncio
async def test_add_run_async():
    t = AddTool()
    assert await t.run(2, 3) == 5


@pytest.mark.integration
def test_add_run_sync():
    t = AddTool()
    assert t.run_sync(2, 3) == 5


@pytest.mark.integration
@pytest.mark.asyncio
async def test_add_run_stream():
    t = AddTool()
    out = []
    async for item in t.run_stream(2, 3):
        out.append(item)

    assert out == [5]


# -------------------------
# WEB SEARCH (async tool, real internet)
# -------------------------
@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
async def test_web_search_run_async_returns_list():
    """
    Real integration test hitting the internet.
    Uses retries because DDG can rate-limit intermittently.
    """
    t = WebSearchTool()

    async def _call():
        return await t.run("openai", max_results=3)

    results = await _retry_async(_call, attempts=3, delay_s=1.5)

    assert isinstance(results, list)
    # Best-effort: could be 0 if rate limited, but should never exceed max_results
    assert len(results) <= 3


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
async def test_web_search_run_sync_raises():
    """
    WebSearchTool registers an async function, so run_sync MUST raise
    (by design of _base.py).
    """
    t = WebSearchTool()
    with pytest.raises(RuntimeError):
        t.run_sync("openai", max_results=3)


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
async def test_web_search_run_stream_yields_items():
    """
    Streaming mode: web_search returns a list[dict], so run_stream()
    should yield each dict item one-by-one.
    """
    t = WebSearchTool()

    async def _call_stream():
        out = []
        async for item in t.run_stream("openai", max_results=3):
            out.append(item)
        return out

    out = await _retry_async(_call_stream, attempts=3, delay_s=1.5)

    assert isinstance(out, list)
    assert len(out) <= 3
    for item in out:
        assert isinstance(item, dict)
