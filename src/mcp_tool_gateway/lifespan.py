from __future__ import annotations

import inspect
import logging
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger("mcp_tool_gateway.lifespan")


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def startup_subapp(app: Any, *, name: str = "subapp") -> None:
    """
    Best-effort startup hook for a mounted ASGI app.

    Some Starlette apps (and MCP's SSE app) rely on startup/shutdown handlers
    to initialize background tasks or session routing. When such an app is
    mounted into a parent FastAPI app, its lifespan may not run automatically.
    This helper forwards startup/shutdown calls from the parent lifespan.
    """
    try:
        if hasattr(app, "startup") and callable(getattr(app, "startup")):
            logger.debug("Starting %s via app.startup()", name)
            await _maybe_await(app.startup())
            return

        router = getattr(app, "router", None)
        if router is not None and hasattr(router, "startup") and callable(getattr(router, "startup")):
            logger.debug("Starting %s via app.router.startup()", name)
            await _maybe_await(router.startup())
            return

        # Some apps expose on_startup list; Starlette's startup() already covers this.
        logger.debug("No explicit startup hook found for %s; skipping", name)
    except Exception:
        logger.exception("Startup failed for %s", name)
        raise


async def shutdown_subapp(app: Any, *, name: str = "subapp") -> None:
    try:
        if hasattr(app, "shutdown") and callable(getattr(app, "shutdown")):
            logger.debug("Stopping %s via app.shutdown()", name)
            await _maybe_await(app.shutdown())
            return

        router = getattr(app, "router", None)
        if router is not None and hasattr(router, "shutdown") and callable(getattr(router, "shutdown")):
            logger.debug("Stopping %s via app.router.shutdown()", name)
            await _maybe_await(router.shutdown())
            return

        logger.debug("No explicit shutdown hook found for %s; skipping", name)
    except Exception:
        logger.exception("Shutdown failed for %s", name)
        raise
