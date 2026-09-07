"""Application settings, loaded from environment / .env."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Database
    database_url: str = "sqlite+aiosqlite:///./gamerlog.db"

    # JWT auth
    jwt_secret: str = "dev-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # CORS — comma-separated origins, read from the CORS_ORIGINS env var.
    # Kept as a plain str (not list[str]): pydantic-settings tries to
    # JSON-decode env values for complex/list-typed fields before any
    # validator runs, which blows up on a plain "http://a,http://b" string.
    # A str field skips that decoding entirely; cors_origins below splits it.
    cors_origins_raw: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="CORS_ORIGINS",
    )

    # Where the frontend lives (Steam login redirects back here with a token).
    frontend_url: str = "http://localhost:5173"

    # External APIs (populated in later steps)
    rawg_api_key: str | None = None
    steam_api_key: str | None = None
    openai_api_key: str | None = None

    @property
    def cors_origins(self) -> list[str]:
        # Trailing slashes are stripped: browsers send Origin as scheme://host,
        # never with a path, so "https://x.app/" would silently never match.
        return [
            o.strip().rstrip("/")
            for o in self.cors_origins_raw.split(",")
            if o.strip().rstrip("/")
        ]

    @property
    def async_database_url(self) -> str:
        """Normalize a plain Postgres URL to the async (asyncpg) driver."""
        url = self.database_url
        if url.startswith("postgresql+asyncpg://"):
            return url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://"):  # some providers use this scheme
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    @property
    def sync_database_url(self) -> str:
        """Sync driver URL (used by Alembic migrations)."""
        url = self.database_url
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql://", 1)
        if url.startswith("sqlite+aiosqlite://"):
            return url.replace("sqlite+aiosqlite://", "sqlite://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
