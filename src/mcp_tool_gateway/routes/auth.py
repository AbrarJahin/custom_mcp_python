from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from ..config import get_settings
from ..security import api_key_is_allowed, issue_jwt


router = APIRouter(tags=["Auth"])


class TokenRequest(BaseModel):
    subject: str = Field("client", description="Subject (sub) claim for the token")
    # If omitted, defaults to MCP_REQUIRED_SCOPES (or empty)
    scopes: Optional[list[str]] = Field(None, description="Optional scopes to include in the token")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post("/auth/token", response_model=TokenResponse)
def create_token(
    body: TokenRequest,
    x_api_key: str = Header("", alias="X-API-Key"),
) -> TokenResponse:
    settings = get_settings()

    if not settings.mcp_enable_auth:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Auth is disabled (MCP_ENABLE_AUTH=false)")

    if not api_key_is_allowed(x_api_key, settings):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    scopes = body.scopes if body.scopes is not None else settings.mcp_required_scopes
    token = issue_jwt(subject=body.subject, scopes=scopes, settings=settings)
    return TokenResponse(access_token=token, expires_in=int(settings.mcp_jwt_ttl_seconds))
