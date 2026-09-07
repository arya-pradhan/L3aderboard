"""Game model — canonical game metadata sourced from RAWG."""
from __future__ import annotations

from datetime import date

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class Game(SQLModel, table=True):
    __tablename__ = "games"

    id: int | None = Field(default=None, primary_key=True)
    # RAWG's own game id; unique so we can upsert/dedupe imports.
    rawg_id: int | None = Field(default=None, index=True, unique=True)
    title: str = Field(index=True, max_length=500)

    # List-valued metadata stored as JSON columns.
    genres: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    platforms: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    cover_url: str | None = Field(default=None, max_length=1000)
    release_date: date | None = Field(default=None)
    description: str | None = Field(default=None)
