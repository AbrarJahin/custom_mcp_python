from __future__ import annotations

import re
from functools import lru_cache
from typing import List

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(value: str) -> list[str]:
    """Split comma/space-separated env strings into a clean list."""
    if value is None:
        return []
    s = str(value).strip()
    if not s:
        return []
    # allow either commas or whitespace or both
    parts = re.split(r"[\s,]+", s)
    return [p for p in (p.strip() for p in parts) if p]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # App
    app_name: str = Field("mcp-tool-gateway", alias="APP_NAME")
    host: str = Field("127.0.0.1", alias="HOST")
    port: int = Field(8000, alias="PORT")
    public_base_url: HttpUrl = Field("http://127.0.0.1:8000", alias="PUBLIC_BASE_URL")

    # MCP
    mcp_name: str = Field("mcp-tool-gateway", alias="MCP_NAME")
    mcp_mount_path: str = Field("/mcp", alias="MCP_MOUNT_PATH")

    # Auth toggles
    mcp_enable_auth: bool = Field(False, alias="MCP_ENABLE_AUTH")
    mcp_api_keys_raw: str = Field("", alias="MCP_API_KEYS")

    # JWT (used only if enable_auth)
    mcp_jwt_secret: str = Field("change-me", alias="MCP_JWT_SECRET")
    mcp_jwt_issuer: str = Field("http://127.0.0.1:8000", alias="MCP_JWT_ISSUER")
    mcp_jwt_audience: str = Field("mcp-clients", alias="MCP_JWT_AUDIENCE")
    mcp_jwt_algorithm: str = Field("HS256", alias="MCP_JWT_ALGORITHM")
    mcp_jwt_ttl_seconds: int = Field(3600, alias="MCP_JWT_TTL_SECONDS")

    # Scopes (optional)
    mcp_required_scopes_raw: str = Field("", alias="MCP_REQUIRED_SCOPES")

    @property
    def mcp_api_keys(self) -> list[str]:
        return _split_csv(self.mcp_api_keys_raw)

    @property
    def mcp_required_scopes(self) -> list[str]:
        return _split_csv(self.mcp_required_scopes_raw)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Singleton settings object for the whole app
    return Settings()
