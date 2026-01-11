from __future__ import annotations
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import logging

import httpx

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.requests import Request
from starlette.responses import Response

from mcp_tool_gateway.config import get_settings
from mcp_tool_gateway.server import mcp
from mcp_tool_gateway.lifespan import startup_subapp, shutdown_subapp
from mcp_tool_gateway.tools import register_all_tools

from mcp_tool_gateway.routes.auth import router as auth_router
from mcp_tool_gateway.routes.tools import router as tools_router

from mcp_tool_gateway.security.middleware import McpAuthGateMiddleware
from mcp_tool_gateway.security import require_scopes, verify_jwt_from_header

logger = logging.getLogger("mcp_tool_gateway.app")


def create_app() -> FastAPI:
    settings = get_settings()

    # Ensure tools are registered before any transport apps are created.
    # This is idempotent (safe to call more than once).
    register_all_tools()

    # Build MCP SSE sub-application once per process.
    # When mounting under a subpath, newer SDK versions recommend passing the
    # mount path so the initial `endpoint` event contains the correct POST URL.
    try:
        mcp_app = mcp.sse_app(settings.mcp_mount_path)
    except TypeError:
        # Older SDK versions don't accept a mount path argument.
        mcp_app = mcp.sse_app()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.debug(
            "Gateway lifespan start: app_name=%s host=%s port=%s mcp_mount_path=%s auth_enabled=%s",
            settings.app_name,
            settings.host,
            settings.port,
            settings.mcp_mount_path,
            settings.mcp_enable_auth,
        )
        # IMPORTANT:
        # FastMCP's HTTP/SSE transports rely on the session manager being started.
        # When embedding (mounting) into FastAPI, you must run that lifespan.
        # (See MCP Python SDK docs: use `mcp.session_manager.run()` in your app lifespan.)
        session_manager = getattr(mcp, "session_manager", None)
        sm_cm = None
        if session_manager is not None and hasattr(session_manager, "run"):
            try:
                sm_cm = session_manager.run()
            except Exception:
                sm_cm = None

        # Forward startup to mounted MCP app (fallback for older versions).
        await startup_subapp(mcp_app, name="mcp_sse_app")

        try:
            if sm_cm is not None and hasattr(sm_cm, "__aenter__"):
                async with sm_cm:
                    yield
            else:
                yield
        finally:
            await shutdown_subapp(mcp_app, name="mcp_sse_app")
            logger.debug("Gateway lifespan stop")

    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    @app.get("/health")
    def health():
        logger.debug("/health called")
        return {
            "ok": True,
            "app_name": settings.app_name,
            "mcp_mount_path": settings.mcp_mount_path,
            "auth_enabled": settings.mcp_enable_auth,
            "time": datetime.now(timezone.utc).isoformat()
        }

    # Register auth endpoint (it will error if auth is disabled, which is fine)
    app.include_router(auth_router)
    app.include_router(tools_router)

    # Streaming-safe auth gate for MCP routes
    if settings.mcp_enable_auth:
        app.add_middleware(McpAuthGateMiddleware, settings=settings)

    # Mount MCP SSE app
    # NOTE: FastMCP also supports streamable_http_app() in newer versions; SSE is the most common.
    #
    # IMPORTANT COMPAT:
    # Many clients (including our integration tests) assume the MCP SSE app is available
    # at the conventional "/mcp" prefix (i.e., /mcp/sse). You may configure a different
    # mount path via MCP_MOUNT_PATH, but for compatibility we also expose the same MCP app
    # under "/mcp". This does NOT remove or change existing behavior; it only adds an
    # additional stable alias.
    # MCP SSE app is created above as mcp_app

    # Primary mount (configurable)
    app.mount(settings.mcp_mount_path, mcp_app)

    logger.debug('Mounted MCP app at %s (and alias /mcp if needed)', settings.mcp_mount_path)

    # Compatibility mount (stable default)
    primary = settings.mcp_mount_path.rstrip("/") or "/"
    if primary != "/mcp":
        app.mount("/mcp", mcp_app)

    # ---------------------------------------------------------------------
    # Compatibility alias: /messages
    # ---------------------------------------------------------------------
    # Some MCP SSE clients resolve the POST "messages" endpoint without the
    # mount prefix (e.g., "/messages" instead of "/mcp/messages"). When the
    # server is mounted under MCP_MOUNT_PATH, that can cause MCP requests
    # (including `initialize`) to be sent to a non-existent route and hang.
    #
    # To preserve the current workflow (MCP mounted at MCP_MOUNT_PATH) while
    # remaining compatible with both endpoint styles, we provide a thin in-process
    # ASGI proxy for POST /messages that forwards to the mounted MCP app.
    @app.post("/messages")
    async def mcp_messages_alias(request: Request) -> Response:
        # If auth is enabled, enforce the same checks as the MCP mount path.
        # (Middleware only guards paths under MCP_MOUNT_PATH.)
        if settings.mcp_enable_auth:
            authorization = request.headers.get("authorization", "")
            claims = verify_jwt_from_header(authorization=authorization, settings=settings)
            require_scopes(claims=claims, settings=settings)

        body = await request.body()

        # Preserve query params (FastMCP uses them for session routing).
        # Example: POST /messages?session_id=...  (dropping this breaks initialize())
        upstream_path = request.url.path
        if request.url.query:
            upstream_path = f"{upstream_path}?{request.url.query}"

        # Forward the request to the MCP ASGI app without making a network call.
        transport = httpx.ASGITransport(app=mcp_app)
        headers = dict(request.headers)
        headers.pop("host", None)

        async with httpx.AsyncClient(transport=transport, base_url="http://mcp") as client:
            upstream = await client.post(
                upstream_path,
                content=body,
                headers=headers,
                timeout=None,  # MCP message handling should control its own timing
            )

        # Drop hop-by-hop headers that shouldn't be forwarded back.
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

    # Nice JSON error for 404 under root
    @app.exception_handler(404)
    async def not_found(_, __):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    return app


app = create_app()
