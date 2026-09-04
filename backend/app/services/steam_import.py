"""Orchestrates importing a user's Steam library into GamerLog.

Flow per owned game: match it to RAWG metadata by title (falling back to a
title-only Game when there's no match), then create or refresh the user's
LibraryEntry with source=steam_import and the Steam playtime.
"""
from __future__ import annotations

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import LibraryEntry, LibrarySource, LibraryStatus, User
from app.schemas.steam import SteamImportSummary
from app.services import rawg, steam
from app.services.games import get_or_create_game_by_title, upsert_game_from_rawg


async def import_library(
    session: AsyncSession, user: User, *, limit: int | None = None
) -> SteamImportSummary:
    """Import (or refresh) the user's Steam-owned games. Requires user.steam_id."""
    owned = await steam.get_owned_games(user.steam_id)
    if limit is not None:
        owned = owned[:limit]

    created = updated = matched = unmatched = 0

    for sg in owned:
        # Try to enrich with RAWG metadata; fall back to title-only.
        rawg_matches = await rawg.search_games(sg.name, limit=1)
        if rawg_matches:
            game = await upsert_game_from_rawg(session, rawg_matches[0])
            matched += 1
        else:
            game = await get_or_create_game_by_title(session, sg.name)
            unmatched += 1

        hours = round(sg.playtime_minutes / 60.0, 1)
        existing = (
            await session.exec(
                select(LibraryEntry).where(
                    LibraryEntry.user_id == user.id,
                    LibraryEntry.game_id == game.id,
                )
            )
        ).first()

        if existing is None:
            session.add(
                LibraryEntry(
                    user_id=user.id,
                    game_id=game.id,
                    status=LibraryStatus.backlog,
                    hours_played=hours,
                    source=LibrarySource.steam_import,
                )
            )
            created += 1
        else:
            # Refresh playtime from Steam; leave the user's status/rating intact.
            existing.hours_played = hours
            session.add(existing)
            updated += 1

    await session.commit()
    return SteamImportSummary(
        total_owned=len(owned),
        created=created,
        updated=updated,
        matched_rawg=matched,
        unmatched=unmatched,
    )
