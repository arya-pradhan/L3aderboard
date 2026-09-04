"""Steam-related schemas."""
from __future__ import annotations

from pydantic import BaseModel


class SteamGame(BaseModel):
    """A game owned on Steam (normalized from GetOwnedGames)."""

    appid: int
    name: str
    playtime_minutes: int = 0


class SteamImportSummary(BaseModel):
    """Result of importing a user's Steam library."""

    total_owned: int
    created: int          # new library entries added
    updated: int          # existing entries whose playtime was refreshed
    matched_rawg: int     # games matched to RAWG metadata
    unmatched: int        # games stored by title only (no RAWG match)
