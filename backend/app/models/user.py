"""User model."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=50)
    # Nullable so a Steam-only account (no email/password) is representable.
    email: str | None = Field(default=None, index=True, unique=True, max_length=255)
    # Nullable so a Steam-only account (no password) is representable.
    hashed_password: str | None = Field(default=None)
    # Set once a Steam account is linked (step 4).
    steam_id: str | None = Field(default=None, index=True, unique=True)
    created_at: datetime = Field(
        default_factory=_utcnow, sa_type=DateTime(timezone=True), nullable=False
    )
