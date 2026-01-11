"""
Integration tests for a locally running MCP server (NO MOCKS).

Assumptions:
- You start the server separately with: make dev
- Server uses .env for HOST/PORT etc (we read env/.env/.env.example)
- Tests connect over MCP SSE and call real tools.

This file is designed to NEVER hang indefinitely:
- All MCP operations are wrapped in asyncio.wait_for timeouts.
- SSE context is always closed in finally blocks.
"""

from __future__ import annotations

import asyncio
import logging
import json
import os
from pathlib import Path
from typing import Any, Optional

import httpx
import pytest
from dotenv import dotenv_values

from mcp import ClientSession
from mcp.client.sse import sse_client

log = logging.getLogger("test_mcp_integration")

# ---------------------------
# Config loading (env -> .env -> .env.example)
# ---------------------------

def _load_value(key: str, default: str = "") -> str:
    if os.getenv(key):
        return os.getenv(key) or default

    env_path = Path(".env")
    if env_path.exists():
        v = dotenv_values(env_path).get(key)
        if v:
            return str(v)

    ex_path = Path(".env.example")
    if ex_path.exists():
        v = dotenv_values(ex_path).get(key)
        if v:
            return str(v)

    return default


HOST = _load_value("HOST", "127.0.0.1")
PORT = _load_value("PORT", "8080")
MCP_MOUNT_PATH = _load_value("MCP_MOUNT_PATH", "/mcp").rstrip("/")

BASE_URL = _load_value("PUBLIC_BASE_URL", f"http://{HOST}:{PORT}")
if not BASE_URL.startswith("http"):
    BASE_URL = f"http://{HOST}:{PORT}"
BASE_URL = BASE_URL.rstrip("/")

MCP_SSE_URL = f"{BASE_URL}{MCP_MOUNT_PATH}/sse"

log.debug('Resolved: HOST=%s PORT=%s BASE_URL=%s MCP_MOUNT_PATH=%s MCP_SSE_URL=%s', HOST, PORT, BASE_URL, MCP_MOUNT_PATH, MCP_SSE_URL)

# Optional auth
MCP_API_KEYS = _load_value("MCP_API_KEYS", "dev-key-1")

# Timeouts to prevent hanging
HTTP_TIMEOUT_S = float(_load_value("TEST_HTTP_TIMEOUT_S", "10"))
MCP_STEP_TIMEOUT_S = float(_load_value("TEST_MCP_STEP_TIMEOUT_S", "15"))

log = logging.getLogger("tests.mcp")
logging.basicConfig(level=logging.DEBUG)


# ---------------------------
# Helpers
# ---------------------------

def _first_api_key() -> str:
    parts = [p.strip() for p in MCP_API_KEYS.split(",") if p.strip()]
    return parts[0] if parts else "dev-key-1"


async def _http_get_json(path: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_S) as client:
        r = await client.get(f"{BASE_URL}{path}")
        log.debug('HTTP GET %s -> %s', path, r.status_code)
        log.debug('HTTP GET %s body(head)=%r', path, r.text[:800])
        r.raise_for_status()
        return r.json()


async def _maybe_get_bearer_token(health: dict[str, Any]) -> Optional[str]:
    """
    Only request a token if the server reports auth_enabled=true in /health.
    """
    if not bool(health.get("auth_enabled", False)):
        return None

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_S) as client:
        r = await client.post(
            f"{BASE_URL}/auth/token",
            headers={"X-API-Key": _first_api_key()},
            json={"subject": "pytest"},
        )
        r.raise_for_status()
        return r.json()["access_token"]


def _extract_text(result: Any) -> str:
    """
    MCP CallToolResult usually contains a list of content blocks.
    We join text blocks into one string.
    """
    if result is None:
        return ""
    content = getattr(result, "content", None)
    if not content:
        return ""
    out: list[str] = []
    for blk in content:
        t = getattr(blk, "text", None)
        if isinstance(t, str):
            out.append(t)
    return "".join(out).strip()


def _try_parse_json(text: str) -> Any:
    if not text:
        return text
    try:
        return json.loads(text)
    except Exception:
        return text


async def _wait(coro, *, timeout_s: float, label: str):
    """
    Wrap an awaitable with a timeout so pytest never hangs.
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout_s)
    except asyncio.TimeoutError as e:
        # Recheck health to distinguish server-down vs handshake-stuck.
        try:
            h = await _http_get_json('/health')
            log.debug('Timeout while %s; /health still OK: %s', label, h)
        except Exception as _:
            log.debug('Timeout while %s; /health recheck failed', label)
        raise AssertionError(f"Timed out after {timeout_s:.0f}s while waiting for: {label}") from e



async def _sniff_sse(url: str, headers: dict[str, str] | None) -> None:
    """
    Best-effort: open SSE and read the first line (if any).
    Helps diagnose buffering / handshake issues.
    """
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_S) as client:
            async with client.stream("GET", url, headers=headers) as r:
                log.debug("SSE SNIFF status=%s headers(content-type)=%s", r.status_code, r.headers.get("content-type"))
                async for line in r.aiter_lines():
                    if line:
                        log.debug("SSE SNIFF first line=%r", line[:300])
                        break
    except Exception as e:
        log.debug("SSE SNIFF failed: %s", repr(e))
async def _open_mcp_session() -> tuple[ClientSession, Any]:
    """
    Opens SSE connection + initializes MCP session.
    Returns (session, sse_ctx) where sse_ctx must be closed.
    """
    health = await _http_get_json("/health")
    token = await _maybe_get_bearer_token(health)
    headers = {"Authorization": f"Bearer {token}"} if token else None

    # Optional: sniff SSE to ensure server is emitting
    await _sniff_sse(MCP_SSE_URL, headers)

    # Open SSE stream
    sse_ctx = sse_client(MCP_SSE_URL, headers=headers)
    read, write = await _wait(
        sse_ctx.__aenter__(),
        timeout_s=MCP_STEP_TIMEOUT_S,
        label=f"open SSE stream {MCP_SSE_URL}",
    )

    session = ClientSession(read, write)

    # Initialize MCP
    await _wait(
        session.initialize(),
        timeout_s=MCP_STEP_TIMEOUT_S,
        label="MCP session.initialize()",
    )

    return session, sse_ctx


async def _close_mcp_session(sse_ctx: Any) -> None:
    await _wait(
        sse_ctx.__aexit__(None, None, None),
        timeout_s=MCP_STEP_TIMEOUT_S,
        label="close SSE context",
    )


async def _retry(coro_factory, *, attempts: int = 3, delay_s: float = 1.5):
    last: Exception | None = None
    for i in range(attempts):
        try:
            return await coro_factory()
        except Exception as e:
            last = e
            if i < attempts - 1:
                await asyncio.sleep(delay_s)
    assert last is not None
    raise last


# ---------------------------
# Tests (NO MOCKS)
# ---------------------------

@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_ok():
    health = await _http_get_json("/health")
    assert health.get("ok") is True
    assert "auth_enabled" in health
    assert "mcp_mount_path" in health


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tools_http_list_ok():
    tools = await _http_get_json("/tools")
    assert isinstance(tools, list)
    names = {t.get("name") for t in tools if isinstance(t, dict)}
    assert "ping" in names
    assert "add" in names
    assert "web_search" in names


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_list_tools_over_sse():
    session, sse_ctx = await _open_mcp_session()
    try:
        tools = await _wait(
            session.list_tools(),
            timeout_s=MCP_STEP_TIMEOUT_S,
            label="MCP session.list_tools()",
        )
        tool_names = {t.name for t in tools.tools}
        assert "ping" in tool_names
        assert "add" in tool_names
        assert "web_search" in tool_names
    finally:
        await _close_mcp_session(sse_ctx)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_ping_tool():
    session, sse_ctx = await _open_mcp_session()
    try:
        result = await _wait(
            session.call_tool("ping", arguments={}),
            timeout_s=MCP_STEP_TIMEOUT_S,
            label='MCP call_tool("ping")',
        )
        text = _extract_text(result).lower()
        assert "pong" in text
    finally:
        await _close_mcp_session(sse_ctx)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_add_tool():
    session, sse_ctx = await _open_mcp_session()
    try:
        result = await _wait(
            session.call_tool("add", arguments={"a": 2, "b": 3}),
            timeout_s=MCP_STEP_TIMEOUT_S,
            label='MCP call_tool("add")',
        )
        text = _extract_text(result)
        assert "5" in text
    finally:
        await _close_mcp_session(sse_ctx)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_web_search_tool_returns_results():
    """
    Real network call. No mocks.
    Retried because DDG/network can be transiently flaky.
    """
    session, sse_ctx = await _open_mcp_session()
    try:
        async def _call():
            return await _wait(
                session.call_tool("web_search", arguments={"query": "openai", "max_results": 3}),
                timeout_s=max(MCP_STEP_TIMEOUT_S, 30),  # allow web search a bit longer
                label='MCP call_tool("web_search")',
            )

        result = await _retry(_call, attempts=3, delay_s=1.5)
        text = _extract_text(result)
        parsed = _try_parse_json(text)

        if isinstance(parsed, list):
            assert len(parsed) >= 1
            assert isinstance(parsed[0], dict)
            assert "title" in parsed[0]
            assert "url" in parsed[0]
            assert "snippet" in parsed[0]
        else:
            # If returned as non-JSON text, still require non-empty
            assert isinstance(text, str) and len(text) > 0
    finally:
        await _close_mcp_session(sse_ctx)
