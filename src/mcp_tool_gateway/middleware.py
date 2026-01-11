from __future__ import annotations

from typing import Any, Callable

from mcp_tool_gateway.security import require_scopes, verify_jwt_from_header


class McpAuthGateMiddleware:
    """
    Streaming-safe ASGI middleware.

    Why: FastAPI/Starlette's BaseHTTPMiddleware (used by @app.middleware("http"))
    is not safe for SSE/streaming responses and can break MCP initialization.

    Behavior:
    - If settings.mcp_enable_auth is False: no auth checks (same as your current env toggle).
    - If True: requests under settings.mcp_mount_path require Authorization: Bearer <jwt>
      and scope validation.
    """

    def __init__(self, app: Callable, *, settings: Any) -> None:
        self.app = app
        self.settings = settings

    async def __call__(self, scope, receive, send) -> None:
        # Only handle HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "") or ""

        # Enforce auth only if enabled AND request is under MCP mount path
        if self.settings.mcp_enable_auth and path.startswith(self.settings.mcp_mount_path):
            # ASGI headers are List[Tuple[bytes, bytes]]
            headers = dict(scope.get("headers") or [])
            auth_bytes = headers.get(b"authorization", b"")
            authorization = auth_bytes.decode("utf-8", errors="ignore")

            claims = verify_jwt_from_header(authorization=authorization, settings=self.settings)
            require_scopes(claims=claims, settings=self.settings)

        await self.app(scope, receive, send)
