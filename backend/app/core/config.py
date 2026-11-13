"""Application settings, loaded from environment / .env."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Repo-root `.env.local` is written by `neon deploy` / `neon env pull`.
# Missing files are skipped, so this is a no-op on Render (env comes from the dashboard).
NEON_ENV_FILE = Path(__file__).resolve().parents[3] / ".env.local"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Later files win: Neon's .env.local overrides a local backend/.env.
        env_file=(".env", NEON_ENV_FILE), env_file_encoding="utf-8", extra="ignore"
    )

    # Database. On Neon: DATABASE_URL is the pooled (-pooler) URL for app
    # traffic; DATABASE_URL_UNPOOLED is the direct URL, used for migrations.
    database_url: str = "sqlite+aiosqlite:///./gamerlog.db"
    database_url_unpooled: str | None = None

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
    deepseek_api_key: str | None = None
    deepseek_model: str = "deepseek-flash"  # = DeepSeek-V4.1-Flash-1017

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
        """App connection URL, normalized for asyncpg."""
        return _to_asyncpg(self.database_url)

    @property
    def migration_database_url(self) -> str:
        """Alembic URL: the direct connection when one is configured, since
        migrations need session state that PgBouncer's pooler doesn't keep."""
        return _to_asyncpg(self.database_url_unpooled or self.database_url)

    @property
    def uses_pgbouncer(self) -> bool:
        return "-pooler" in self.database_url

    @property
    def sync_database_url(self) -> str:
        """Sync driver URL (Alembic offline `--sql` mode)."""
        url = self.database_url_unpooled or self.database_url
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql://", 1)
        if url.startswith("sqlite+aiosqlite://"):
            return url.replace("sqlite+aiosqlite://", "sqlite://", 1)
        return url


def _to_asyncpg(url: str) -> str:
    """Normalize a plain Postgres URL to the async (asyncpg) driver."""
    for prefix in ("postgresql+asyncpg://", "postgresql://", "postgres://"):
        if url.startswith(prefix):
            return _asyncpg_query("postgresql+asyncpg://" + url[len(prefix):])
    return url


def _asyncpg_query(url: str) -> str:
    """asyncpg rejects libpq's `sslmode` / `channel_binding` params (Neon puts
    both in its URLs); translate sslmode into asyncpg's `ssl` instead."""
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query.pop("channel_binding", None)
    sslmode = query.pop("sslmode", None)
    if sslmode and "ssl" not in query:
        query["ssl"] = sslmode
    return urlunsplit(parts._replace(query=urlencode(query)))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
