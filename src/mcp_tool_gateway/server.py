import os
from mcp.server.fastmcp import FastMCP

ENABLE_AUTH = os.getenv("MCP_ENABLE_AUTH", "false").lower() in ("1", "true", "yes")

kwargs = dict(
    name="mcp-tool-gateway",
    # other normal FastMCP args...
)

if ENABLE_AUTH:
    # ONLY set these when auth settings are present
    # kwargs["auth_settings"] = ...
    kwargs["auth_server_provider"] = ...
    # OR kwargs["token_verifier"] = ...
    # (whatever you were setting before)

mcp = FastMCP(**kwargs)
