"""RAWG API client.

Isolated, framework-agnostic wrapper around the RAWG video-game database
(https://rawg.io/apidocs). Returns normalized `RawgGame` objects so the rest of
the app never deals with RAWG's raw JSON shape. Raises service-level exceptions
that route handlers translate into HTTP responses.

Discovery reads (`discover_games`, `list_genres`) are identical for every user
and go through a small in-process TTL cache, since RAWG's free tier allows
~20k requests/month and the home page would otherwise hit it on every load.
"""
from __future__ import annotations

import time
from datetime import date, datetime
from typing import Any

import httpx

from app.core.config import settings
from app.schemas.game import RawgGame

RAWG_BASE_URL = "https://api.rawg.io/api"
_TIMEOUT = httpx.Timeout(10.0)
CACHE_TTL_SECONDS = 30 * 60


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


# --- tiny TTL cache ------------------------------------------------------

_cache: dict[str, tuple[float, Any]] = {}


def _cache_get(key: str) -> Any | None:
    hit = _cache.get(key)
    if hit is not None and hit[0] > time.monotonic():
        return hit[1]
    _cache.pop(key, None)
    return None


def _cache_set(key: str, value: Any) -> None:
    _cache[key] = (time.monotonic() + CACHE_TTL_SECONDS, value)


def clear_cache() -> None:
    """Exposed for tests."""
    _cache.clear()


# --- normalization -------------------------------------------------------


def _normalize(raw: dict) -> RawgGame:
    """Map a RAWG game object onto our normalized RawgGame schema."""
    # RAWG returns null (not just an absent key) for these on some games, so
    # `.get(key, [])` isn't enough — coerce None to [] explicitly.
    genres = [g["name"] for g in (raw.get("genres") or []) if g.get("name")]
    # RAWG mixes tag languages; keep English tags for clean recommender features.
    tags = [
        t["name"]
        for t in (raw.get("tags") or [])
        if t.get("name") and t.get("language") == "eng"
    ]
    platforms = [
        p["platform"]["name"]
        for p in (raw.get("platforms") or [])
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
        # Only present on the detail endpoint, not in list/search results.
        description=(raw.get("description_raw") or None),
    )


# --- requests ------------------------------------------------------------


async def _fetch_games(
    params: dict[str, Any], *, cache_key: str | None = None
) -> list[RawgGame]:
    """GET /games with the given filters, normalized (optionally cached)."""
    if cache_key:
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

    key = _require_key()
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{RAWG_BASE_URL}/games", params={"key": key, **params}
            )
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise RAWGError(f"RAWG request failed: {exc}") from exc

    games = [_normalize(r) for r in resp.json().get("results", [])]
    if cache_key:
        _cache_set(cache_key, games)
    return games


async def search_games(query: str, *, limit: int = 10) -> list[RawgGame]:
    """Search RAWG by title, returning normalized results."""
    return await _fetch_games({"search": query, "page_size": limit})


async def discover_games(*, limit: int = 20, **filters: Any) -> list[RawgGame]:
    """Browse RAWG by filter (ordering, dates, genres, ...). Cached."""
    params = {k: v for k, v in filters.items() if v is not None}
    params["page_size"] = limit
    cache_key = "games:" + "&".join(f"{k}={params[k]}" for k in sorted(params))
    return await _fetch_games(params, cache_key=cache_key)


async def list_genres() -> list[dict[str, str]]:
    """RAWG's genre list as [{slug, name}, ...]. Cached."""
    cached = _cache_get("genres")
    if cached is not None:
        return cached

    key = _require_key()
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{RAWG_BASE_URL}/genres", params={"key": key, "page_size": 40}
            )
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise RAWGError(f"RAWG genres request failed: {exc}") from exc

    genres = [
        {"slug": g["slug"], "name": g["name"]}
        for g in resp.json().get("results", [])
        if g.get("slug") and g.get("name")
    ]
    _cache_set("genres", genres)
    return genres


async def get_game(rawg_id: int) -> RawgGame:
    """Fetch a single game's full metadata (incl. description) by RAWG id."""
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
