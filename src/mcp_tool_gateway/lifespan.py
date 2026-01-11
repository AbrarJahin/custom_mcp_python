"""Minimal helpers for starting/stopping subapps.

Note: For MCP SSE transport we avoid calling FastMCP internals directly.
"""
from __future__ import annotations

import inspect
from typing import Any

async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value

async def startup_subapp(app: Any, *, name: str = "subapp") -> None:
    # Keep for compatibility; used only if sub-app has startup hooks.
    if hasattr(app, "startup") and callable(getattr(app, "startup")):
        await _maybe_await(app.startup())

async def shutdown_subapp(app: Any, *, name: str = "subapp") -> None:
    if hasattr(app, "shutdown") and callable(getattr(app, "shutdown")):
        await _maybe_await(app.shutdown())
