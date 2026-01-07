from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from fastapi import HTTPException, status

from .config import Settings


def api_key_is_allowed(api_key: str, settings: Settings) -> bool:
    api_key = (api_key or "").strip()
    return bool(api_key) and api_key in set(settings.mcp_api_keys)


def issue_jwt(*, subject: str, scopes: list[str], settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=int(settings.mcp_jwt_ttl_seconds))

    payload: Dict[str, Any] = {
        "sub": subject,
        "iss": settings.mcp_jwt_issuer,
        "aud": settings.mcp_jwt_audience,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "scope": " ".join(scopes),
    }
    return jwt.encode(payload, settings.mcp_jwt_secret, algorithm=settings.mcp_jwt_algorithm)


def _extract_bearer_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header")
    return parts[1].strip()


def verify_jwt_from_header(*, authorization: Optional[str], settings: Settings) -> Dict[str, Any]:
    token = _extract_bearer_token(authorization)
    try:
        claims = jwt.decode(
            token,
            settings.mcp_jwt_secret,
            algorithms=[settings.mcp_jwt_algorithm],
            audience=settings.mcp_jwt_audience,
            issuer=settings.mcp_jwt_issuer,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
        return claims
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def require_scopes(*, claims: Dict[str, Any], settings: Settings) -> None:
    required = set(settings.mcp_required_scopes)
    if not required:
        return

    scope_str = str(claims.get("scope") or "")
    token_scopes = set([s for s in scope_str.split() if s])
    missing = required - token_scopes
    if missing:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing scopes: {', '.join(sorted(missing))}")
