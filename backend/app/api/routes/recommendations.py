"""Content-based game recommendations for the current user."""
from __future__ import annotations

from fastapi import APIRouter, Query
from sqlmodel import select

from app.core.deps import CurrentUser, SessionDep
from app.models import Game, LibraryEntry, LibraryStatus
from app.schemas.game import GameRead
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


def _build_liked(entries, games_by_id) -> list[LikedItem]:
    """Pick the signal to build a taste profile from, best available first."""

    def feats(entry):
        game = games_by_id.get(entry.game_id)
        return extract_features(game.genres, game.tags) if game else []

    high = [e for e in entries if e.rating is not None and e.rating >= LIKED_RATING]
    if high:
        return [LikedItem(features=feats(e), weight=float(e.rating)) for e in high]

    rated = [e for e in entries if e.rating is not None]
    if rated:
        return [LikedItem(features=feats(e), weight=float(e.rating)) for e in rated]

    implicit = [e for e in entries if e.status in IMPLICIT_POSITIVE]
    return [LikedItem(features=feats(e), weight=1.0) for e in implicit]


@router.get("/recommendations", response_model=list[GameRead])
async def get_recommendations(
    current_user: CurrentUser,
    session: SessionDep,
    limit: int = Query(default=12, ge=1, le=40),
) -> list[GameRead]:
    entries = (
        await session.exec(
            select(LibraryEntry).where(LibraryEntry.user_id == current_user.id)
        )
    ).all()
    if not entries:
        return []

    owned_ids = {e.game_id for e in entries}
    owned_games = (
        await session.exec(select(Game).where(Game.id.in_(owned_ids)))
    ).all()
    games_by_id = {g.id: g for g in owned_games}

    liked = _build_liked(entries, games_by_id)
    if not liked:
        return []

    # Candidates: everything in the catalog the user doesn't already have.
    candidate_games = (
        await session.exec(select(Game).where(Game.id.notin_(owned_ids)))
    ).all()
    candidates = [
        CandidateItem(key=g.id, features=extract_features(g.genres, g.tags))
        for g in candidate_games
    ]
    candidate_by_id = {g.id: g for g in candidate_games}

    scored = recommend(liked, candidates, limit=limit)
    return [GameRead.model_validate(candidate_by_id[s.key]) for s in scored]
