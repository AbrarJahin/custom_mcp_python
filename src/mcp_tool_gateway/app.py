from __future__ import annotations

import contextlib

from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from .server import mcp


async def health(request):
    return JSONResponse({"ok": True})


@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    # Required when mounting the streamable-http app
    async with mcp.session_manager.run():
        yield


starlette_app = Starlette(
    debug=False,
    routes=[
        Route("/health", health, methods=["GET"]),
        # Clients connect to http://host:port/mcp
        Mount("/mcp", app=mcp.streamable_http_app()),
    ],
    lifespan=lifespan,
)

# Optional: enable CORS for browser-based clients / inspector
app = CORSMiddleware(
    starlette_app,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE"],
    expose_headers=["Mcp-Session-Id"],
)
