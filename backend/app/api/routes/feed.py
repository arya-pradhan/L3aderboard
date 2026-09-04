"""Activity feed — recent library changes from users you follow.

Derived on the fly from LibraryEntry rows (no separate event log), per the
project's data-model decision.
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from sqlmodel import select

from app.core.deps import CurrentUser, SessionDep
from app.models import Follow, Game, LibraryEntry, User
from app.schemas.game import GameRead
from app.schemas.social import FeedActor, FeedItem

router = APIRouter(tags=["feed"])


@router.get("/feed", response_model=list[FeedItem])
async def activity_feed(
    current_user: CurrentUser,
    session: SessionDep,
    limit: int = Query(default=50, ge=1, le=100),
) -> list[FeedItem]:
    followed_ids = (
        await session.exec(
            select(Follow.followed_id).where(Follow.follower_id == current_user.id)
        )
    ).all()
    if not followed_ids:
        return []

    entries = (
        await session.exec(
            select(LibraryEntry)
            .where(LibraryEntry.user_id.in_(followed_ids))
            .order_by(LibraryEntry.updated_at.desc())
            .limit(limit)
        )
    ).all()
    if not entries:
        return []

    # Batch-load the referenced games and actors to avoid N+1 queries.
    game_ids = {e.game_id for e in entries}
    games = (await session.exec(select(Game).where(Game.id.in_(game_ids)))).all()
    game_map = {g.id: g for g in games}

    user_ids = {e.user_id for e in entries}
    users = (await session.exec(select(User).where(User.id.in_(user_ids)))).all()
    user_map = {u.id: u for u in users}

    return [
        FeedItem(
            entry_id=e.id,
            user=FeedActor(id=e.user_id, username=user_map[e.user_id].username),
            status=e.status,
            rating=e.rating,
            hours_played=e.hours_played,
            updated_at=e.updated_at,
            game=GameRead.model_validate(game_map[e.game_id]),
        )
        for e in entries
    ]
