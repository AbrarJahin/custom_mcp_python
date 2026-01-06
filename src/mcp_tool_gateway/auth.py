from __future__ import annotations

from dataclasses import dataclass

from mcp.server.auth.provider import AccessToken, TokenVerifier

from .config import settings


@dataclass
class ApiKeyToken(AccessToken):
    """Represents an authenticated caller.

    We keep this minimal for a starter template. In production, add:
    - subject / agent_id
    - role
    - allowed_tools
    - tenant_id
    """
    token: str
    client_id: str | None = None
    scope: str | None = None


class SimpleApiKeyVerifier(TokenVerifier):
    """Accepts `Authorization: Bearer <key>` where <key> is in MCP_API_KEYS.

    The MCP SDK supports OAuth-based resource server verification as well; this is a
    pragmatic starter that you can swap later.
    """

    async def verify_token(self, token: str) -> AccessToken | None:
        if token in settings.api_keys():
            return ApiKeyToken(token=token, client_id="agent")
        return None
