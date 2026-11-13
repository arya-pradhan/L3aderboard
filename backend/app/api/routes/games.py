"""Game search routes (RAWG passthrough)."""
# NOTE: no `from __future__ import annotations` — see auth.py; slowapi's
# wrapper breaks FastAPI's resolution of string-typed dependencies.
from fastapi import APIRouter, Query, Request

from app.core.deps import CurrentUser
from app.core.ratelimit import DETAIL_LIMIT, SEARCH_LIMIT, limiter, user_or_ip
from app.schemas.game import RawgGame
from app.services import rawg

router = APIRouter(prefix="/games", tags=["games"])


@router.get("/search", response_model=list[RawgGame])
@limiter.limit(SEARCH_LIMIT, key_func=user_or_ip)
async def search_games(
    request: Request,
    current_user: CurrentUser,
    q: str = Query(min_length=1, description="Game title to search for"),
    limit: int = Query(default=10, ge=1, le=40),
) -> list[RawgGame]:
    return await rawg.search_games(q, limit=limit)


@router.get("/{rawg_id}", response_model=RawgGame)
@limiter.limit(DETAIL_LIMIT, key_func=user_or_ip)
async def get_game(
    request: Request, rawg_id: int, current_user: CurrentUser
) -> RawgGame:
    """Full metadata for one RAWG game, including its description.

    Search results omit the description, so the add-to-library modal fetches
    this for a game that isn't in the user's library yet.
    """
    return await rawg.get_game(rawg_id)
