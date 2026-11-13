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

    rows = (
        await session.exec(
            select(LibraryEntry, Game, User)
            .join(Game, Game.id == LibraryEntry.game_id)
            .join(User, User.id == LibraryEntry.user_id)
            .where(LibraryEntry.user_id.in_(followed_ids))
            .order_by(LibraryEntry.updated_at.desc())
            .limit(limit)
        )
    ).all()

    return [
        FeedItem(
            entry_id=e.id,
            user=FeedActor(id=u.id, username=u.username),
            status=e.status,
            rating=e.rating,
            hours_played=e.hours_played,
            updated_at=e.updated_at,
            game=GameRead.model_validate(g),
        )
        for e, g, u in rows
    ]
