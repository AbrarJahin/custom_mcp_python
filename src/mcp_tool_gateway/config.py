from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(value: str | None) -> list[str]:
    """Split comma/space-separated env strings into a clean list."""
    if value is None:
        return []
    s = str(value).strip()
    if not s:
        return []
    parts = re.split(r"[\s,]+", s)
    return [p for p in (p.strip() for p in parts) if p]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # -----------------------------
    # App
    # -----------------------------
    app_name: str = Field("mcp-tool-gateway", alias="APP_NAME")
    host: str = Field("127.0.0.1", alias="HOST")
    port: int = Field(8080, alias="PORT")
    public_base_url: HttpUrl = Field("http://127.0.0.1:8080", alias="PUBLIC_BASE_URL")

    # -----------------------------
    # MCP
    # -----------------------------
    mcp_name: str = Field("mcp-tool-gateway", alias="MCP_NAME")
    mcp_mount_path: str = Field("/mcp", alias="MCP_MOUNT_PATH")

    # Enable auth middleware on the FastAPI gateway for MCP routes.
    mcp_enable_auth: bool = Field(False, alias="MCP_ENABLE_AUTH")

    # Simple API-key list (comma/space separated)
    mcp_api_keys_raw: str = Field("", alias="MCP_API_KEYS")

    # JWT settings (used only if MCP_ENABLE_AUTH=true)
    mcp_jwt_secret: str = Field("change-me", alias="MCP_JWT_SECRET")
    mcp_jwt_issuer: str = Field("http://127.0.0.1:8080", alias="MCP_JWT_ISSUER")
    mcp_jwt_audience: str = Field("mcp-clients", alias="MCP_JWT_AUDIENCE")
    mcp_jwt_algorithm: str = Field("HS256", alias="MCP_JWT_ALGORITHM")
    mcp_jwt_ttl_seconds: int = Field(3600, alias="MCP_JWT_TTL_SECONDS")
    mcp_required_scopes_raw: str = Field("", alias="MCP_REQUIRED_SCOPES")

    # -----------------------------
    # Tools: Files
    # -----------------------------
    files_base_dir: str = Field("./data", alias="FILES_BASE_DIR")

    # -----------------------------
    # Tools: Web
    # -----------------------------
    # Domain allowlist for web fetch. Empty = deny all for safety.
    web_allowed_domains_raw: str = Field("", alias="WEB_ALLOWED_DOMAINS")
    web_fetch_timeout_s: float = Field(15.0, alias="WEB_FETCH_TIMEOUT_S")
    web_max_bytes: int = Field(1_000_000, alias="WEB_MAX_BYTES")
    web_user_agent: str = Field("mcp-tool-gateway/0.1", alias="WEB_USER_AGENT")

    @property
    def mcp_api_keys(self) -> list[str]:
        return _split_csv(self.mcp_api_keys_raw)

    @property
    def mcp_required_scopes(self) -> list[str]:
        return _split_csv(self.mcp_required_scopes_raw)

    def allowed_domains(self) -> list[str]:
        """Allowlist of domains for web fetching. Empty means deny all."""
        return [d.lower().strip(".") for d in _split_csv(self.web_allowed_domains_raw)]

    def files_base_path(self) -> Path:
        return Path(self.files_base_dir).expanduser()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


# Convenience singleton (importable by services/tools)
settings = get_settings()
