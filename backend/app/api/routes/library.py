"""Library CRUD — the current user's games, statuses, ratings and reviews."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError

from app.core.deps import CurrentUser, SessionDep
from app.models import Game, LibraryEntry, LibrarySource, LibraryStatus
from app.schemas.game import (
    LibraryEntryCreate,
    LibraryEntryRead,
    LibraryEntryUpdate,
)
from app.schemas.steam import SteamImportSummary
from app.services import rawg, steam_import
from app.services.games import upsert_game_from_rawg
from app.services.library_view import entry_to_read, user_library

router = APIRouter(prefix="/library", tags=["library"])


async def _get_owned_entry(
    session: SessionDep, entry_id: int, user_id: int
) -> LibraryEntry:
    entry = await session.get(LibraryEntry, entry_id)
    # Treat "not yours" as "not found" so we don't leak other users' entry ids.
    if entry is None or entry.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Library entry not found"
        )
    return entry


@router.get("", response_model=list[LibraryEntryRead])
async def list_my_library(
    current_user: CurrentUser,
    session: SessionDep,
    status_filter: LibraryStatus | None = Query(default=None, alias="status"),
) -> list[LibraryEntryRead]:
    return await user_library(session, current_user.id, status_filter)


@router.post("", response_model=LibraryEntryRead, status_code=status.HTTP_201_CREATED)
async def add_to_library(
    payload: LibraryEntryCreate,
    current_user: CurrentUser,
    session: SessionDep,
) -> LibraryEntryRead:
    # Fetch authoritative metadata from RAWG (client only sends the rawg_id).
    game = await upsert_game_from_rawg(session, await rawg.get_game(payload.rawg_id))

    entry = LibraryEntry(
        user_id=current_user.id,
        game_id=game.id,
        status=payload.status,
        rating=payload.rating,
        review_text=payload.review_text,
        hours_played=payload.hours_played,
        source=LibrarySource.manual,
    )
    session.add(entry)
    try:
        await session.commit()
    except IntegrityError:  # uq_library_user_game: already in the library
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Game already in your library",
        )
    await session.refresh(entry)
    return entry_to_read(entry, game)


@router.post("/steam/import", response_model=SteamImportSummary)
async def import_from_steam(
    current_user: CurrentUser,
    session: SessionDep,
) -> SteamImportSummary:
    if not current_user.steam_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Steam account linked. Sign in with Steam first.",
        )
    return await steam_import.import_library(session, current_user)


@router.patch("/{entry_id}", response_model=LibraryEntryRead)
async def update_entry(
    entry_id: int,
    payload: LibraryEntryUpdate,
    current_user: CurrentUser,
    session: SessionDep,
) -> LibraryEntryRead:
    entry = await _get_owned_entry(session, entry_id, current_user.id)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(entry, field, value)
    if updates:
        entry.updated_at = datetime.now(timezone.utc)

    session.add(entry)
    await session.commit()
    await session.refresh(entry)

    game = await session.get(Game, entry.game_id)
    return entry_to_read(entry, game)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: int,
    current_user: CurrentUser,
    session: SessionDep,
) -> Response:
    entry = await _get_owned_entry(session, entry_id, current_user.id)
    await session.delete(entry)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
