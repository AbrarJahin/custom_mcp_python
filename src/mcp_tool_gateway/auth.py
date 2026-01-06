from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from mcp.server.auth.provider import AccessToken, TokenVerifier

from .config import settings


@dataclass
class ApiKeyToken(AccessToken):
    """Minimal authenticated caller identity.

    In production you can extend this with:
    - subject / agent_id
    - role
    - tenant_id
    - scopes
    """

    token: str
    client_id: str
    expires_at: Optional[float] = None
    scope: Optional[str] = None


class SimpleApiKeyVerifier(TokenVerifier):
    """Accepts `Authorization: Bearer <key>` where <key> is in MCP_API_KEYS."""

    async def verify_token(self, token: str) -> AccessToken | None:
        if token in settings.api_keys():
            return ApiKeyToken(token=token, client_id="agent")
        return None
