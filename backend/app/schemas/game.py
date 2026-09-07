"""Game and library-entry schemas."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models import LibrarySource, LibraryStatus


class RawgGame(BaseModel):
    """Normalized game metadata returned by the RAWG service."""

    rawg_id: int
    title: str
    genres: list[str] = []
    tags: list[str] = []
    platforms: list[str] = []
    cover_url: str | None = None
    release_date: date | None = None
    # RAWG only returns this from its detail endpoint, so it's None for
    # search/browse results.
    description: str | None = None


class GameRead(BaseModel):
    """A game as stored in our database."""

    id: int
    rawg_id: int | None = None
    title: str
    genres: list[str] = []
    tags: list[str] = []
    platforms: list[str] = []
    cover_url: str | None = None
    release_date: date | None = None
    description: str | None = None

    model_config = {"from_attributes": True}


class DiscoveryRow(BaseModel):
    """One horizontal row on the home page."""

    key: str
    title: str
    subtitle: str | None = None
    games: list[RawgGame] = []


class LibraryEntryCreate(BaseModel):
    """Add a game (by RAWG id) to the current user's library."""

    rawg_id: int
    status: LibraryStatus = LibraryStatus.backlog
    rating: int | None = Field(default=None, ge=1, le=10)
    review_text: str | None = None
    hours_played: float = Field(default=0.0, ge=0)


class LibraryEntryUpdate(BaseModel):
    """Partial update of a library entry. All fields optional."""

    status: LibraryStatus | None = None
    rating: int | None = Field(default=None, ge=1, le=10)
    review_text: str | None = None
    hours_played: float | None = Field(default=None, ge=0)


class LibraryEntryRead(BaseModel):
    id: int
    status: LibraryStatus
    rating: int | None
    review_text: str | None
    hours_played: float
    source: LibrarySource
    created_at: datetime
    updated_at: datetime
    game: GameRead

    model_config = {"from_attributes": True}
