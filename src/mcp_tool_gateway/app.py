from __future__ import annotations
from datetime import datetime, timezone

import httpx

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.requests import Request
from starlette.responses import Response

from mcp_tool_gateway.config import get_settings
from mcp_tool_gateway.server import mcp

from mcp_tool_gateway.routes.auth import router as auth_router
from mcp_tool_gateway.routes.tools import router as tools_router

from mcp_tool_gateway.middleware import McpAuthGateMiddleware
from mcp_tool_gateway.security import require_scopes, verify_jwt_from_header


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(title=settings.app_name)

    @app.get("/health")
    def health():
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
    mcp_app = mcp.sse_app()

    # Primary mount (configurable)
    app.mount(settings.mcp_mount_path, mcp_app)

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
