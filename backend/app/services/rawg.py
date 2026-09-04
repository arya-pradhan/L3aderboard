"""RAWG API client.

Isolated, framework-agnostic wrapper around the RAWG video-game database
(https://rawg.io/apidocs). Returns normalized `RawgGame` objects so the rest of
the app never deals with RAWG's raw JSON shape. Raises service-level exceptions
that route handlers translate into HTTP responses.
"""
from __future__ import annotations

from datetime import date, datetime

import httpx

from app.core.config import settings
from app.schemas.game import RawgGame

RAWG_BASE_URL = "https://api.rawg.io/api"
_TIMEOUT = httpx.Timeout(10.0)


class RAWGError(RuntimeError):
    """Generic upstream/transport error talking to RAWG."""


class RAWGNotConfigured(RAWGError):
    """RAWG_API_KEY is not set."""


class RAWGNotFound(RAWGError):
    """A specific RAWG resource was not found."""


def _require_key() -> str:
    if not settings.rawg_api_key:
        raise RAWGNotConfigured(
            "RAWG_API_KEY is not configured. Add it to the backend .env."
        )
    return settings.rawg_api_key


def _parse_release_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _normalize(raw: dict) -> RawgGame:
    """Map a RAWG game object onto our normalized RawgGame schema."""
    genres = [g["name"] for g in raw.get("genres", []) if g.get("name")]
    # RAWG mixes tag languages; keep English tags for clean recommender features.
    tags = [
        t["name"]
        for t in raw.get("tags", [])
        if t.get("name") and t.get("language") == "eng"
    ]
    platforms = [
        p["platform"]["name"]
        for p in raw.get("platforms", []) or []
        if p.get("platform", {}).get("name")
    ]
    return RawgGame(
        rawg_id=raw["id"],
        title=raw.get("name", "Unknown"),
        genres=genres,
        tags=tags,
        platforms=platforms,
        cover_url=raw.get("background_image"),
        release_date=_parse_release_date(raw.get("released")),
    )


async def search_games(query: str, *, limit: int = 10) -> list[RawgGame]:
    """Search RAWG by title, returning normalized results."""
    key = _require_key()
    params = {"key": key, "search": query, "page_size": limit}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"{RAWG_BASE_URL}/games", params=params)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise RAWGError(f"RAWG search failed: {exc}") from exc
    results = resp.json().get("results", [])
    return [_normalize(r) for r in results]


async def get_game(rawg_id: int) -> RawgGame:
    """Fetch a single game's full metadata by RAWG id."""
    key = _require_key()
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{RAWG_BASE_URL}/games/{rawg_id}", params={"key": key}
            )
            if resp.status_code == 404:
                raise RAWGNotFound(f"RAWG game {rawg_id} not found")
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise RAWGError(f"RAWG lookup failed: {exc}") from exc
    return _normalize(resp.json())
