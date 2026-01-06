from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8000

    # Simple bearer-key auth (comma-separated)
    mcp_api_keys: str = "dev-key-1"

    # Web tools
    web_allowed_domains: str = "example.com"
    web_fetch_timeout_s: float = 12.0
    web_max_bytes: int = 800_000

    # File tools
    files_base_dir: str = "./data"

    def api_keys(self) -> set[str]:
        return {k.strip() for k in self.mcp_api_keys.split(",") if k.strip()}

    def allowed_domains(self) -> set[str]:
        return {d.strip().lower() for d in self.web_allowed_domains.split(",") if d.strip()}


settings = Settings()
