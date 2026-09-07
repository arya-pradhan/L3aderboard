"""Content-based game recommendations for the current user.

Candidates come from RAWG (browsed by the user's favourite genres) rather than
only the local catalog — otherwise a fresh deployment has nothing to recommend
from. Ranking stays in `services/recommender.py`, which remains pure.
"""
from __future__ import annotations

import asyncio
from collections import Counter

from fastapi import APIRouter, Query
from sqlmodel import select

from app.core.deps import CurrentUser, SessionDep
from app.models import Game, LibraryEntry, LibraryStatus
from app.schemas.game import RawgGame
from app.services import rawg
from app.services.recommender import (
    CandidateItem,
    LikedItem,
    extract_features,
    recommend,
)

router = APIRouter(tags=["recommendations"])

# Ratings at or above this count as an explicit "like".
LIKED_RATING = 7
# Statuses that signal an implicit positive when the user hasn't rated anything.
IMPLICIT_POSITIVE = {LibraryStatus.completed, LibraryStatus.playing}
# How many genres of the user's taste to pull candidates for.
CANDIDATE_GENRES = 3
CANDIDATES_PER_GENRE = 20


def _liked_entries(entries) -> list:
    """Pick the strongest available taste signal."""
    high = [e for e in entries if e.rating is not None and e.rating >= LIKED_RATING]
    if high:
        return high
    rated = [e for e in entries if e.rating is not None]
    if rated:
        return rated
    return [e for e in entries if e.status in IMPLICIT_POSITIVE]


def _build_liked(entries, games_by_id) -> list[LikedItem]:
    items = []
    for entry in entries:
        game = games_by_id.get(entry.game_id)
        if game is None:
            continue
        items.append(
            LikedItem(
                features=extract_features(game.genres, game.tags),
                weight=float(entry.rating) if entry.rating is not None else 1.0,
            )
        )
    return items


async def _candidate_pool(
    liked_games: list[Game], owned_rawg_ids: set[int]
) -> list[RawgGame]:
    """Browse RAWG for games in the user's favourite genres."""
    counts = Counter(g for game in liked_games for g in (game.genres or []))
    if not counts:
        return []

    try:
        slug_by_name = {g["name"].lower(): g["slug"] for g in await rawg.list_genres()}
    except rawg.RAWGError:
        return []

    slugs = [
        slug_by_name[name.lower()]
        for name, _ in counts.most_common(CANDIDATE_GENRES)
        if name.lower() in slug_by_name
    ]
    if not slugs:
        return []

    results = await asyncio.gather(
        *(
            rawg.discover_games(
                limit=CANDIDATES_PER_GENRE, ordering="-added", genres=slug
            )
            for slug in slugs
        ),
        return_exceptions=True,
    )

    pool: dict[int, RawgGame] = {}
    for result in results:
        if isinstance(result, BaseException):
            continue
        for game in result:
            if game.rawg_id not in owned_rawg_ids:
                pool.setdefault(game.rawg_id, game)
    return list(pool.values())


@router.get("/recommendations", response_model=list[RawgGame])
async def get_recommendations(
    current_user: CurrentUser,
    session: SessionDep,
    limit: int = Query(default=12, ge=1, le=40),
) -> list[RawgGame]:
    entries = (
        await session.exec(
            select(LibraryEntry).where(LibraryEntry.user_id == current_user.id)
        )
    ).all()
    if not entries:
        return []

    owned_ids = {e.game_id for e in entries}
    owned_games = (await session.exec(select(Game).where(Game.id.in_(owned_ids)))).all()
    games_by_id = {g.id: g for g in owned_games}
    owned_rawg_ids = {g.rawg_id for g in owned_games if g.rawg_id is not None}

    signal = _liked_entries(entries)
    liked = _build_liked(signal, games_by_id)
    if not liked:
        return []

    liked_games = [games_by_id[e.game_id] for e in signal if e.game_id in games_by_id]
    pool = await _candidate_pool(liked_games, owned_rawg_ids)
    if not pool:
        return []

    candidates = [
        CandidateItem(key=i, features=extract_features(g.genres, g.tags))
        for i, g in enumerate(pool)
    ]
    scored = recommend(liked, candidates, limit=limit)
    return [pool[s.key] for s in scored]
