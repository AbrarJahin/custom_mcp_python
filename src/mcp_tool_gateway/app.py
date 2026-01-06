from __future__ import annotations

import contextlib

from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from .server import mcp


@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    # Required when mounting streamable-http app into ASGI server
    async with mcp.session_manager.run():
        yield


async def health(_: object) -> JSONResponse:
    return JSONResponse({"ok": True})


app = Starlette(
    routes=[
        Route("/health", health, methods=["GET"]),
        # Mount MCP server. Clients connect to http://host:port/mcp citeturn4view0
        Mount("/", app=mcp.streamable_http_app()),
    ],
    lifespan=lifespan,
)

# Optional: enable CORS for browser-based MCP clients. citeturn4view0
app = CORSMiddleware(
    app,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE"],
    expose_headers=["Mcp-Session-Id"],
)
