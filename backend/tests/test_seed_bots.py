"""The bot seeder, run against the in-memory DB with RAWG faked."""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from pydantic import EmailStr, TypeAdapter
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Follow, LibraryEntry, User
from app.schemas.game import RawgGame
from scripts.seed_bots import (
    ACTIVITY_WINDOW_DAYS,
    MAX_GAMES,
    MIN_GAMES,
    PERSONAS,
    seed,
)


async def fake_source(slug: str) -> list[RawgGame]:
    # 20 distinct games per genre, ids namespaced by slug so genres don't collide.
    base = (sum(map(ord, slug)) % 97) * 1000
    return [
        RawgGame(rawg_id=base + i, title=f"{slug} game {i}", genres=[slug.title()])
        for i in range(20)
    ]


async def test_seed_creates_personas_with_realistic_libraries(session: AsyncSession) -> None:
    now = datetime.now(timezone.utc)
    summary = await seed(
        session, game_source=fake_source, password="pw", rng=random.Random(1), now=now
    )

    assert sorted(summary.created_users) == sorted(p.username for p in PERSONAS)
    assert summary.skipped_users == []

    users = (await session.exec(select(User))).all()
    assert len(users) == len(PERSONAS)
    assert all(u.hashed_password for u in users)  # log-in-able
    # Bot emails must satisfy the same validator real registrations do —
    # a reserved TLD (.local) once made /auth/me 500 for every bot.
    email_validator = TypeAdapter(EmailStr)
    for u in users:
        email_validator.validate_python(u.email)

    for user in users:
        entries = (
            await session.exec(select(LibraryEntry).where(LibraryEntry.user_id == user.id))
        ).all()
        assert MIN_GAMES <= len(entries) <= MAX_GAMES
        for e in entries:
            # Activity spread over the recent window, so the feed reads as live.
            age = now - e.updated_at.replace(tzinfo=timezone.utc)
            assert timedelta(0) <= age <= timedelta(days=ACTIVITY_WINDOW_DAYS)
            assert e.created_at <= e.updated_at
            # Ratings only where the status implies an opinion.
            if e.status.value == "backlog":
                assert e.rating is None and e.hours_played == 0
            elif e.rating is not None:
                assert 1 <= e.rating <= 10

    follows = (await session.exec(select(Follow))).all()
    assert summary.follows == len(follows) > 0


async def test_seed_is_idempotent(session: AsyncSession) -> None:
    first = await seed(session, game_source=fake_source, password="pw", rng=random.Random(2))
    entries_after_first = len((await session.exec(select(LibraryEntry))).all())

    second = await seed(session, game_source=fake_source, password="pw", rng=random.Random(3))

    assert second.created_users == []
    assert sorted(second.skipped_users) == sorted(first.created_users)
    assert second.entries == 0
    assert len((await session.exec(select(LibraryEntry))).all()) == entries_after_first
    # Re-running doesn't duplicate follow edges either.
    assert second.follows == 0
