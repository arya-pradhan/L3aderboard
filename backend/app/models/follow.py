"""Follow model — directed edge: follower_id follows followed_id."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Follow(SQLModel, table=True):
    __tablename__ = "follows"

    follower_id: int = Field(foreign_key="users.id", primary_key=True)
    followed_id: int = Field(foreign_key="users.id", primary_key=True)
    created_at: datetime = Field(
        default_factory=_utcnow, sa_type=DateTime(timezone=True), nullable=False
    )
