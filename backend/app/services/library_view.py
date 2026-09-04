"""Shared helper for serializing LibraryEntry + Game into read schemas.

Lives in services (not a route module) so multiple routers can reuse it
without importing each other.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Game, LibraryEntry
from app.schemas.game import GameRead, LibraryEntryRead


def entry_to_read(entry: LibraryEntry, game: Game) -> LibraryEntryRead:
    return LibraryEntryRead(
        id=entry.id,
        status=entry.status,
        rating=entry.rating,
        review_text=entry.review_text,
        hours_played=entry.hours_played,
        source=entry.source,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
        game=GameRead.model_validate(game),
    )


async def entries_to_reads(
    session: AsyncSession, entries: Sequence[LibraryEntry]
) -> list[LibraryEntryRead]:
    """Batch-load the games referenced by entries and build read models."""
    if not entries:
        return []
    game_ids = {e.game_id for e in entries}
    games: Iterable[Game] = (
        await session.exec(select(Game).where(Game.id.in_(game_ids)))
    ).all()
    game_map = {g.id: g for g in games}
    return [entry_to_read(e, game_map[e.game_id]) for e in entries]
