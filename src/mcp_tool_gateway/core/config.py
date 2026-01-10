from __future__ import annotations

import re
from functools import lru_cache

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(value: str) -> list[str]:
    """Split comma/space-separated env strings into a clean list."""
    if value is None:
        return []
    s = str(value).strip()
    if not s:
        return []
    # split on commas or whitespace
    parts = re.split(r"[\s,]+", s)
    return [p.strip().lower().strip(".") for p in parts if p.strip()]


class Settings(BaseSettings):
    """App settings loaded from environment and optional .env file."""

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
    port: int = Field(8000, alias="PORT")
    public_base_url: HttpUrl = Field("http://127.0.0.1:8000", alias="PUBLIC_BASE_URL")

    # -----------------------------
    # MCP
    # -----------------------------
    mcp_name: str = Field("mcp-tool-gateway", alias="MCP_NAME")
    mcp_mount_path: str = Field("/mcp", alias="MCP_MOUNT_PATH")

    # -----------------------------
    # Auth toggles (FastAPI middleware + optional token issuance endpoint)
    # -----------------------------
    mcp_enable_auth: bool = Field(False, alias="MCP_ENABLE_AUTH")
    mcp_api_keys_raw: str = Field("", alias="MCP_API_KEYS")  # CSV/space separated
    mcp_required_scopes_raw: str = Field("", alias="MCP_REQUIRED_SCOPES")  # CSV/space separated

    # JWT (issued by /auth/token when auth enabled)
    mcp_jwt_secret: str = Field("dev-secret-change-me", alias="MCP_JWT_SECRET")
    mcp_jwt_algorithm: str = Field("HS256", alias="MCP_JWT_ALGORITHM")
    mcp_jwt_audience: str = Field("mcp-tool-gateway", alias="MCP_JWT_AUDIENCE")
    mcp_jwt_issuer: str = Field("mcp-tool-gateway", alias="MCP_JWT_ISSUER")
    mcp_jwt_ttl_seconds: int = Field(3600, alias="MCP_JWT_TTL_SECONDS")

    # -----------------------------
    # Web tools
    # -----------------------------
    web_allowed_domains_raw: str = Field("", alias="WEB_ALLOWED_DOMAINS")  # CSV/space separated
    web_fetch_timeout_s: float = Field(20.0, alias="WEB_FETCH_TIMEOUT_S")
    web_max_bytes: int = Field(200_000, alias="WEB_MAX_BYTES")

    # -----------------------------
    # File tools
    # -----------------------------
    files_base_dir: str = Field("./data", alias="FILES_BASE_DIR")
    files_max_pages: int = Field(10, alias="FILES_MAX_PAGES")
    files_max_chars: int = Field(50_000, alias="FILES_MAX_CHARS")

    @property
    def mcp_api_keys(self) -> list[str]:
        return _split_csv(self.mcp_api_keys_raw)

    @property
    def mcp_required_scopes(self) -> list[str]:
        return _split_csv(self.mcp_required_scopes_raw)

    def allowed_domains(self) -> list[str]:
        """Parsed allowlist domains for web fetching/search."""
        return _split_csv(self.web_allowed_domains_raw)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton settings object for the whole process."""
    return Settings()


# Convenience singleton (kept for backwards compatibility with existing tool modules)
settings: Settings = get_settings()
