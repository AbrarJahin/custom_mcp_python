from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .core.config import get_settings
from .core.security import require_scopes, verify_jwt_from_header
from .mcp.server import mcp
from .api.router import router as api_router


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


    # API routes (e.g., /auth/token)
    app.include_router(api_router)

    # Optional auth middleware (protect MCP endpoint when enabled)
    @app.middleware("http")
    async def mcp_auth_middleware(request: Request, call_next):
        # Only protect MCP mount path and only when enabled
        if settings.mcp_enable_auth and request.url.path.startswith(settings.mcp_mount_path):
            claims = verify_jwt_from_header(authorization=request.headers.get("authorization"), settings=settings)
            require_scopes(claims=claims, settings=settings)
        return await call_next(request)

    # Mount MCP SSE app
    app.mount(settings.mcp_mount_path, mcp.sse_app())

    @app.exception_handler(404)
    async def not_found(_, __):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    return app


app = create_app()
