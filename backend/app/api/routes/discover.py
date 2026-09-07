"""Home-page discovery rows, sourced live from RAWG.

These are non-personalized (beyond genre choice) and work with an empty library,
which is what makes the home page useful before a user has rated anything.
"""
from __future__ import annotations

import asyncio
from collections import Counter
from datetime import date, timedelta

from fastapi import APIRouter
from sqlmodel import select

from app.core.deps import CurrentUser, SessionDep
from app.models import Game, LibraryEntry
from app.schemas.game import DiscoveryRow
from app.services import rawg

router = APIRouter(prefix="/discover", tags=["discover"])

# Used when the user's library is too thin to infer taste.
DEFAULT_GENRE_SLUGS = ["indie", "action"]
GENRE_ROWS = 2
ROW_SIZE = 20


async def _user_top_genre_slugs(
    session: SessionDep, user_id: int, limit: int = GENRE_ROWS
) -> list[str]:
    """The user's most common library genres, as RAWG slugs."""
    game_ids = (
        await session.exec(
            select(LibraryEntry.game_id).where(LibraryEntry.user_id == user_id)
        )
    ).all()
    if not game_ids:
        return DEFAULT_GENRE_SLUGS[:limit]

    games = (await session.exec(select(Game).where(Game.id.in_(game_ids)))).all()
    counts = Counter(g for game in games for g in (game.genres or []))
    if not counts:
        return DEFAULT_GENRE_SLUGS[:limit]

    try:
        slug_by_name = {g["name"].lower(): g["slug"] for g in await rawg.list_genres()}
    except rawg.RAWGError:
        return DEFAULT_GENRE_SLUGS[:limit]

    slugs = [
        slug_by_name[name.lower()]
        for name, _ in counts.most_common()
        if name.lower() in slug_by_name
    ]
    # Top up with defaults so we always render the same number of rows.
    for fallback in DEFAULT_GENRE_SLUGS:
        if len(slugs) >= limit:
            break
        if fallback not in slugs:
            slugs.append(fallback)
    return slugs[:limit]


async def _row(key: str, title: str, subtitle: str, **filters) -> DiscoveryRow:
    games = await rawg.discover_games(limit=ROW_SIZE, **filters)
    return DiscoveryRow(key=key, title=title, subtitle=subtitle, games=games)


@router.get("/home", response_model=list[DiscoveryRow])
async def home_rows(
    current_user: CurrentUser, session: SessionDep
) -> list[DiscoveryRow]:
    today = date.today()
    year = today.year
    genre_slugs = await _user_top_genre_slugs(session, current_user.id)

    # The two windows are split at today — already-released vs not-yet-released —
    # so the rows don't surface the same titles twice.
    jobs = [
        _row(
            "popular",
            f"Popular in {year}",
            "out this year, and everyone's playing it",
            ordering="-added",
            dates=f"{year}-01-01,{today}",
        ),
        _row(
            "upcoming",
            "New & upcoming",
            "the most anticipated releases ahead",
            ordering="-added",
            dates=f"{today + timedelta(days=1)},{today + timedelta(days=365)}",
        ),
    ]
    for slug in genre_slugs:
        pretty = slug.replace("-", " ").title()
        jobs.append(
            _row(
                f"genre:{slug}",
                pretty,
                "popular in this genre",
                ordering="-added",
                genres=slug,
            )
        )

    # One slow/failing row shouldn't take down the whole home page.
    results = await asyncio.gather(*jobs, return_exceptions=True)
    return [r for r in results if isinstance(r, DiscoveryRow) and r.games]
