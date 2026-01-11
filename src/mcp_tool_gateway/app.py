from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging

import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.requests import Request
from starlette.responses import Response

from mcp_tool_gateway.config import get_settings
from mcp_tool_gateway.server import mcp
from mcp_tool_gateway.tools import register_all_tools
from mcp_tool_gateway.routes import health_router
from mcp_tool_gateway.routes import tools_router
from mcp_tool_gateway.security.middleware import McpAuthGateMiddleware

logger = logging.getLogger("mcp_tool_gateway.app")


def _build_mcp_transport_app(settings):
    """Create the MCP SSE transport app.

    Newer MCP versions accept an optional `mount_path` argument. Older versions do not.
    """
    # IMPORTANT:
    # MCP's FastMCP exposes `session_manager` only after `streamable_http_app()` is called.
    # Some SSE variants internally touch the session manager, so we initialize it once here.
    try:
        mcp.streamable_http_app()
    except Exception:
        # Older versions may not have streamable transport; ignore.
        pass

    try:
        return mcp.sse_app(settings.mcp_mount_path)
    except TypeError:
        return mcp.sse_app()


def create_app() -> FastAPI:
    settings = get_settings()

    # Ensure tools are registered exactly once BEFORE any client hits /mcp/sse.
    register_all_tools()

    mcp_app = _build_mcp_transport_app(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(
            "Gateway lifespan start: app_name=%s host=%s port=%s mcp_mount_path=%s auth_enabled=%s",
            settings.app_name,
            settings.host,
            settings.port,
            settings.mcp_mount_path,
            settings.mcp_enable_auth,
        )
        yield
        logger.info("Gateway lifespan stop")

    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    # Routes
    app.include_router(health_router)
    app.include_router(tools_router)

    # Security middleware (no-op when auth disabled)
    app.add_middleware(McpAuthGateMiddleware)

    # Mount MCP transport
    app.mount(settings.mcp_mount_path, mcp_app)

    # Compatibility alias for /mcp if user changes mount path
    if settings.mcp_mount_path != "/mcp":
        app.mount("/mcp", mcp_app)

    # Compatibility: forward /messages to /mcp/messages (some clients assume root)
    @app.api_route("/messages", methods=["POST"])
    async def messages_alias(request: Request):
        upstream_url = f"{settings.public_base_url}{settings.mcp_mount_path}/messages"
        async with httpx.AsyncClient(timeout=30) as client:
            upstream = await client.request(
                request.method,
                upstream_url,
                params=dict(request.query_params),
                content=await request.body(),
                headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
            )

        hop_by_hop = {
            "connection",
            "keep-alive",
            "proxy-authenticate",
            "proxy-authorization",
            "te",
            "trailers",
            "transfer-encoding",
            "upgrade",
        }
        out_headers = {k: v for k, v in upstream.headers.items() if k.lower() not in hop_by_hop}
        return Response(content=upstream.content, status_code=upstream.status_code, headers=out_headers)

    @app.get("/__meta__")
    async def meta():
        return {
            "app": settings.app_name,
            "mcp_name": settings.mcp_name,
            "mount_path": settings.mcp_mount_path,
            "public_base_url": settings.public_base_url,
            "ts": datetime.now(timezone.utc).isoformat(),
        }

    @app.exception_handler(404)
    async def not_found(_, __):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    return app


app = create_app()
