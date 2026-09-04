"""Social schemas: public profiles and the activity feed."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models import LibraryStatus
from app.schemas.game import GameRead


class UserProfile(BaseModel):
    """Public-facing profile with social counts."""

    id: int
    username: str
    created_at: datetime
    games_count: int
    followers_count: int
    following_count: int
    # Whether the requesting user follows this profile.
    is_following: bool
    # True when this profile is the requesting user's own.
    is_self: bool


class FeedActor(BaseModel):
    id: int
    username: str


class FeedItem(BaseModel):
    """One activity-feed entry: a followed user's recent library change."""

    entry_id: int
    user: FeedActor
    status: LibraryStatus
    rating: int | None
    hours_played: float
    updated_at: datetime
    game: GameRead
