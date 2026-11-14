"""Home-page discovery rows, sourced live from RAWG.

These are non-personalized (beyond genre choice) and work with an empty library,
which is what makes the home page useful before a user has rated anything.
"""
from __future__ import annotations

import asyncio
from collections import Counter
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.core.deps import CurrentUser, SessionDep
from app.models import Game, LibraryEntry
from app.schemas.game import DiscoveryRow, GenreRef, RawgGame
from app.services import rawg

router = APIRouter(prefix="/discover", tags=["discover"])

# Used when the user's library is too thin to infer taste.
DEFAULT_GENRE_SLUGS = ["indie", "action"]
GENRE_ROWS = 2
ROW_SIZE = 40  # RAWG's max page size
# Genres too niche to deserve a home-page shelf.
SKIP_GENRES = {"educational", "board-games", "card", "family"}


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
        slugs = await rawg.genre_slugs([name for name, _ in counts.most_common()])
    except rawg.RAWGError:
        return DEFAULT_GENRE_SLUGS[:limit]

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


@router.get("/genres", response_model=list[GenreRef])
async def genre_shelves(current_user: CurrentUser, session: SessionDep) -> list[GenreRef]:
    """Genres for the home page's shelves: the user's favourites first, then the rest."""
    try:
        genres = [g for g in await rawg.list_genres() if g["slug"] not in SKIP_GENRES]
    except rawg.RAWGError:
        return []
    top = await _user_top_genre_slugs(session, current_user.id, limit=3)
    rank = {slug: i for i, slug in enumerate(top)}
    # sorted() is stable: non-favourites keep RAWG's own (popularity) order.
    return [GenreRef(**g) for g in sorted(genres, key=lambda g: rank.get(g["slug"], len(rank)))]


@router.get("/genre/{slug}", response_model=list[RawgGame])
async def genre_shelf(slug: str, current_user: CurrentUser) -> list[RawgGame]:
    """One genre's shelf. Only RAWG's own genre slugs, so the cache stays bounded."""
    if slug not in {g["slug"] for g in await rawg.list_genres()}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown genre")
    return await rawg.discover_games(limit=ROW_SIZE, ordering="-added", genres=slug)
