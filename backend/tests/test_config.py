"""Regression test: CORS_ORIGINS as a real comma-separated env var must not
crash Settings construction (pydantic-settings JSON-decodes list-typed env
values before validators run, which broke this in production)."""
from __future__ import annotations

from app.core.config import Settings


def test_cors_origins_parses_comma_separated_env(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://a.example.com,https://b.example.com")
    s = Settings()
    assert s.cors_origins == ["https://a.example.com", "https://b.example.com"]


def test_cors_origins_default():
    s = Settings(_env_file=None)
    assert s.cors_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_cors_origins_single_value_no_trailing_slash(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://l3aderboard.vercel.app")
    s = Settings()
    assert s.cors_origins == ["https://l3aderboard.vercel.app"]


def test_cors_origins_strips_trailing_slash(monkeypatch):
    # Browsers send Origin without a trailing slash; a pasted URL often has one.
    monkeypatch.setenv("CORS_ORIGINS", "https://l3aderboard.vercel.app/")
    s = Settings()
    assert s.cors_origins == ["https://l3aderboard.vercel.app"]


def test_cors_origins_mixed_slashes_and_spaces(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://a.app/, https://b.app ,https://c.app/")
    s = Settings()
    assert s.cors_origins == ["https://a.app", "https://b.app", "https://c.app"]


def test_neon_url_normalized_for_asyncpg():
    s = Settings(
        _env_file=None,
        database_url="postgresql://u:p@ep-x.us-east-2.aws.neon.tech/db"
        "?sslmode=require&channel_binding=require",
    )
    assert s.async_database_url == (
        "postgresql+asyncpg://u:p@ep-x.us-east-2.aws.neon.tech/db?ssl=require"
    )


def test_plain_postgres_url_unchanged_besides_driver():
    s = Settings(_env_file=None, database_url="postgres://u:p@localhost:5432/db")
    assert s.async_database_url == "postgresql+asyncpg://u:p@localhost:5432/db"


def test_migrations_prefer_unpooled_url():
    s = Settings(
        _env_file=None,
        database_url="postgresql://u:p@ep-x-pooler.neon.tech/db?sslmode=require",
        database_url_unpooled="postgresql://u:p@ep-x.neon.tech/db?sslmode=require",
    )
    assert s.uses_pgbouncer
    assert s.async_database_url == "postgresql+asyncpg://u:p@ep-x-pooler.neon.tech/db?ssl=require"
    assert s.migration_database_url == "postgresql+asyncpg://u:p@ep-x.neon.tech/db?ssl=require"
