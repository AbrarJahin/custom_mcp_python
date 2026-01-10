from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional

import jwt  # PyJWT

from .config import get_settings

# MCP auth types (provided by the `mcp` package)
from mcp.server.auth.provider import AccessToken, TokenVerifier


@dataclass(frozen=True)
class JwtToken(AccessToken):
    """Access token info returned by our TokenVerifier.

    `mcp` only needs a few standard fields to authorize requests.
    """

    client_id: str
    scopes: List[str]
    expires_at: int  # epoch seconds


class JwtTokenVerifier(TokenVerifier):
    """Verifies Bearer JWTs for the MCP server."""

    async def verify_token(self, token: str) -> Optional[AccessToken]:
        settings = get_settings()

        try:
            payload = jwt.decode(
                token,
                settings.mcp_jwt_secret,
                algorithms=[settings.mcp_jwt_algorithm],
                audience=settings.mcp_jwt_audience,
                issuer=settings.mcp_jwt_issuer,
                options={
                    "require": ["exp", "iat", "sub"],
                },
            )
        except Exception:
            return None

        # scopes: accept either space-separated string ("a b") or list ["a","b"]
        raw_scopes = payload.get("scope") or payload.get("scopes") or ""
        if isinstance(raw_scopes, str):
            scopes = [s for s in raw_scopes.split() if s]
        elif isinstance(raw_scopes, list):
            scopes = [str(s) for s in raw_scopes if s]
        else:
            scopes = []

        exp = int(payload.get("exp", 0) or 0)
        sub = str(payload.get("sub") or "")

        if not sub or exp <= int(time.time()):
            return None

        # enforce required scopes (if configured)
        required = settings.required_scopes_list
        if required and not set(required).issubset(set(scopes)):
            return None

        return JwtToken(client_id=sub, scopes=scopes, expires_at=exp)


def issue_jwt_for_client(
    *,
    client_id: str,
    scopes: Optional[List[str]] = None,
    ttl_seconds: Optional[int] = None,
) -> str:
    """Create a signed JWT for MCP access."""
    settings = get_settings()
    now = int(time.time())

    ttl = int(ttl_seconds or settings.mcp_jwt_ttl_seconds)
    exp = now + ttl

    scope_str = " ".join(scopes or [])

    payload = {
        "sub": client_id,
        "iat": now,
        "exp": exp,
        "iss": settings.mcp_jwt_issuer,
        "aud": settings.mcp_jwt_audience,
        "scope": scope_str,
    }

    return jwt.encode(payload, settings.mcp_jwt_secret, algorithm=settings.mcp_jwt_algorithm)


def is_valid_api_key(api_key: str) -> bool:
    """Simple check for token-issuing endpoint."""
    settings = get_settings()
    if not settings.mcp_api_keys:
        return False
    return api_key in set(settings.mcp_api_keys)
