from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .config import get_settings
from .security import require_scopes, verify_jwt_from_header
from .server import mcp

from .routes.auth import router as auth_router
from .routes.tools import router as tools_router


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
        }

    # Register auth endpoint (it will error if auth is disabled, which is fine)
    app.include_router(auth_router)
    app.include_router(tools_router)

    # Middleware-like gate for MCP routes when auth is enabled.
    @app.middleware("http")
    async def mcp_auth_gate(request: Request, call_next):
        if settings.mcp_enable_auth and request.url.path.startswith(settings.mcp_mount_path):
            claims = verify_jwt_from_header(authorization=request.headers.get("authorization"), settings=settings)
            require_scopes(claims=claims, settings=settings)
        return await call_next(request)

    # Mount MCP SSE app
    # NOTE: FastMCP also supports streamable_http_app() in newer versions; SSE is the most common.
    app.mount(settings.mcp_mount_path, mcp.sse_app())

    # Nice JSON error for 404 under root
    @app.exception_handler(404)
    async def not_found(_, __):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    return app


app = create_app()
