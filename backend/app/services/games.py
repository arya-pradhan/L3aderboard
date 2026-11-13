"""Game persistence helpers — turning RAWG metadata into local Game rows.

Kept separate from route handlers so both manual entry (step 3) and Steam import
(step 4) can reuse the same match-or-create logic.
"""
from __future__ import annotations

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Game
from app.schemas.game import RawgGame


async def upsert_game_from_rawg(session: AsyncSession, data: RawgGame) -> Game:
    """Return the existing Game for this RAWG id, or create it.

    If the game exists, refresh its metadata (RAWG data can change over time).
    The caller is responsible for committing the transaction.
    """
    game = (
        await session.exec(select(Game).where(Game.rawg_id == data.rawg_id))
    ).first() or Game(rawg_id=data.rawg_id, title=data.title)
    # Browse/search results carry no description; don't wipe a stored one.
    for field, value in data.model_dump().items():
        if field != "description" or value:
            setattr(game, field, value)
    session.add(game)
    await session.flush()  # assign game.id without ending the transaction
    return game


async def get_or_create_game_by_title(session: AsyncSession, title: str) -> Game:
    """Fallback for games with no RAWG match (e.g. some Steam titles).

    Dedupes on the title among rows that have no rawg_id, so re-imports don't
    create duplicates. The caller commits the transaction.
    """
    result = await session.exec(
        select(Game).where(Game.rawg_id.is_(None), Game.title == title)
    )
    game = result.first()
    if game is not None:
        return game

    game = Game(rawg_id=None, title=title)
    session.add(game)
    await session.flush()
    return game
