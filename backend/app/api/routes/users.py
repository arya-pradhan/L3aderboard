"""User profile + follow/unfollow routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func
from sqlmodel import select

from app.core.deps import CurrentUser, SessionDep
from app.models import Follow, LibraryEntry, LibraryStatus, User
from app.schemas.game import LibraryEntryRead
from app.schemas.social import SuggestedUser, UserProfile
from app.services.library_view import entries_to_reads

router = APIRouter(prefix="/users", tags=["users"])


async def _get_user_by_username(session: SessionDep, username: str) -> User:
    user = (
        await session.exec(select(User).where(User.username == username))
    ).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


async def _count(session: SessionDep, model, *conditions) -> int:
    stmt = select(func.count()).select_from(model)
    for cond in conditions:
        stmt = stmt.where(cond)
    return (await session.exec(stmt)).one()


# NOTE: declared before "/{username}" — otherwise the literal path segment
# "suggested" is captured as a username and 404s.
@router.get("/suggested", response_model=list[SuggestedUser])
async def suggested_users(
    current_user: CurrentUser,
    session: SessionDep,
    limit: int = Query(default=6, ge=1, le=20),
) -> list[SuggestedUser]:
    """People to follow: users the caller doesn't follow yet, biggest library first."""
    following = (
        await session.exec(
            select(Follow.followed_id).where(Follow.follower_id == current_user.id)
        )
    ).all()
    excluded = set(following) | {current_user.id}

    games_count = func.count(LibraryEntry.id).label("games_count")
    stmt = (
        select(User, games_count)
        .outerjoin(LibraryEntry, LibraryEntry.user_id == User.id)
        .where(User.id.notin_(excluded))
        .group_by(User.id)
        .order_by(games_count.desc(), User.created_at.asc())
        .limit(limit)
    )
    rows = (await session.exec(stmt)).all()

    result = []
    for user, count in rows:
        followers = await _count(session, Follow, Follow.followed_id == user.id)
        result.append(
            SuggestedUser(
                id=user.id,
                username=user.username,
                games_count=count,
                followers_count=followers,
            )
        )
    return result


@router.get("/{username}", response_model=UserProfile)
async def get_profile(
    username: str, current_user: CurrentUser, session: SessionDep
) -> UserProfile:
    user = await _get_user_by_username(session, username)

    games_count = await _count(session, LibraryEntry, LibraryEntry.user_id == user.id)
    followers_count = await _count(session, Follow, Follow.followed_id == user.id)
    following_count = await _count(session, Follow, Follow.follower_id == user.id)

    is_self = user.id == current_user.id
    is_following = False
    if not is_self:
        follow = await session.get(Follow, (current_user.id, user.id))
        is_following = follow is not None

    return UserProfile(
        id=user.id,
        username=user.username,
        created_at=user.created_at,
        games_count=games_count,
        followers_count=followers_count,
        following_count=following_count,
        is_following=is_following,
        is_self=is_self,
    )


@router.get("/{username}/library", response_model=list[LibraryEntryRead])
async def get_user_library(
    username: str,
    current_user: CurrentUser,
    session: SessionDep,
    status_filter: LibraryStatus | None = Query(default=None, alias="status"),
) -> list[LibraryEntryRead]:
    """A user's public library, newest-updated first, filterable by status."""
    user = await _get_user_by_username(session, username)
    stmt = select(LibraryEntry).where(LibraryEntry.user_id == user.id)
    if status_filter is not None:
        stmt = stmt.where(LibraryEntry.status == status_filter)
    stmt = stmt.order_by(LibraryEntry.updated_at.desc())
    entries = (await session.exec(stmt)).all()
    return await entries_to_reads(session, entries)


@router.post("/{username}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def follow_user(
    username: str, current_user: CurrentUser, session: SessionDep
) -> Response:
    target = await _get_user_by_username(session, username)
    if target.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot follow yourself"
        )

    # Idempotent: only create the edge if it doesn't already exist.
    existing = await session.get(Follow, (current_user.id, target.id))
    if existing is None:
        session.add(Follow(follower_id=current_user.id, followed_id=target.id))
        await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{username}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_user(
    username: str, current_user: CurrentUser, session: SessionDep
) -> Response:
    target = await _get_user_by_username(session, username)
    existing = await session.get(Follow, (current_user.id, target.id))
    if existing is not None:
        await session.delete(existing)
        await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
