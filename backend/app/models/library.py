"""LibraryEntry model — a user's relationship to a game (status/rating/review)."""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel, UniqueConstraint


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LibraryStatus(str, enum.Enum):
    playing = "playing"
    completed = "completed"
    dropped = "dropped"
    backlog = "backlog"


class LibrarySource(str, enum.Enum):
    steam_import = "steam_import"
    manual = "manual"


class LibraryEntry(SQLModel, table=True):
    __tablename__ = "library_entries"
    __table_args__ = (
        UniqueConstraint("user_id", "game_id", name="uq_library_user_game"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    game_id: int = Field(foreign_key="games.id", index=True, nullable=False)

    status: LibraryStatus = Field(default=LibraryStatus.backlog, index=True)
    rating: int | None = Field(default=None, ge=1, le=10)
    review_text: str | None = Field(default=None)
    hours_played: float = Field(default=0.0)
    source: LibrarySource = Field(default=LibrarySource.manual)

    created_at: datetime = Field(
        default_factory=_utcnow, sa_type=DateTime(timezone=True), nullable=False
    )
    updated_at: datetime = Field(
        default_factory=_utcnow, sa_type=DateTime(timezone=True), nullable=False
    )
