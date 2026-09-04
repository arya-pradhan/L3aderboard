"""Game search routes (RAWG passthrough)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.core.deps import CurrentUser
from app.schemas.game import RawgGame
from app.services import rawg
from app.services.rawg import RAWGError, RAWGNotConfigured

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
