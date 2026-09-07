"""Game search routes (RAWG passthrough)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.core.deps import CurrentUser
from app.schemas.game import RawgGame
from app.services import rawg
from app.services.rawg import RAWGError, RAWGNotConfigured, RAWGNotFound

router = APIRouter(prefix="/games", tags=["games"])


@router.get("/search", response_model=list[RawgGame])
async def search_games(
    current_user: CurrentUser,
    q: str = Query(min_length=1, description="Game title to search for"),
    limit: int = Query(default=10, ge=1, le=40),
) -> list[RawgGame]:
    try:
        return await rawg.search_games(q, limit=limit)
    except RAWGNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )
    except RAWGError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


@router.get("/{rawg_id}", response_model=RawgGame)
async def get_game(rawg_id: int, current_user: CurrentUser) -> RawgGame:
    """Full metadata for one RAWG game, including its description.

    Search results omit the description, so the add-to-library modal fetches
    this for a game that isn't in the user's library yet.
    """
    try:
        return await rawg.get_game(rawg_id)
    except RAWGNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )
    except RAWGNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RAWGError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
