"""Seed demo "bot" users with realistic libraries so the feed has life.

Usage (from backend/):
    ./.venv/Scripts/python.exe -m scripts.seed_bots

Idempotent: bots that already exist are skipped, so it's safe to re-run (e.g.
against production after a redeploy). Games come from RAWG through the same
`upsert_game_from_rawg` path real adds use, so bots' libraries are real titles
with real art.

Bot accounts are log-in-able so you can test the social features from the other
side. The password comes from the BOT_PASSWORD env var, or is generated and
printed once — it is deliberately NOT a fixed string in the repo, so public
deployments don't ship accounts anyone can hijack.
"""
from __future__ import annotations

import asyncio
import os
import random
import secrets
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.security import hash_password
from app.models import Follow, LibraryEntry, LibrarySource, LibraryStatus, User
from app.schemas.game import RawgGame
from app.services.games import upsert_game_from_rawg

GameSource = Callable[[str], Awaitable[list[RawgGame]]]

ACTIVITY_WINDOW_DAYS = 14
MIN_GAMES, MAX_GAMES = 8, 15
# Must be a syntactically valid, non-reserved domain: pydantic's EmailStr
# rejects special-use TLDs like .local/.test/.example.
BOT_EMAIL_DOMAIN = "l3aderboard.dev"
REVIEW_CHANCE = 0.4
FOLLOWS_PER_BOT = 2


@dataclass(frozen=True)
class Persona:
    username: str
    genres: tuple[str, ...]  # RAWG genre slugs, in order of affinity


PERSONAS: tuple[Persona, ...] = (
    Persona("cozy_kai", ("indie", "simulation", "casual")),
    Persona("souls_sam", ("action", "role-playing-games-rpg")),
    Persona("speedrun_sal", ("platformer", "arcade", "indie")),
    Persona("lorehound", ("role-playing-games-rpg", "adventure")),
    Persona("pixel_penny", ("indie", "puzzle", "platformer")),
    Persona("backlog_bex", ("strategy", "simulation", "adventure")),
)

REVIEWS: tuple[str, ...] = (
    "Put way more hours in than I planned. No regrets.",
    "Brilliant for the first ten hours, then it starts repeating itself.",
    "The map is the quest log. Either that delights you or it doesn't.",
    "Dropped it halfway and I'm at peace with that.",
    "Tight controls, great soundtrack, cruel checkpoints.",
    "Finished it in one weekend. Credits guaranteed.",
    "Never once opened a wiki. That's the highest praise I have.",
    "Gorgeous, but I kept waiting for it to get going.",
    "A perfect podcast game.",
    "Second playthrough already. Send help.",
    "Rated it a 6, then thought about it for a week, then made it an 8.",
    "The kind of game you recommend with a caveat.",
    "More cozy than it looks, more difficult than it admits.",
    "Bought on sale, opened once, will absolutely finish it. Eventually.",
    "Combat carries it. Story is set dressing.",
    "Ran it back immediately. That ending.",
    "Made a spreadsheet. It has tabs.",
    "Great in co-op, lonely solo.",
    "Short, sharp, and knows exactly what it is.",
    "I respect it more than I enjoyed it.",
)

# status -> (weight, rating range or None, hours range)
STATUS_PROFILE = {
    LibraryStatus.completed: (0.40, (7, 10), (10, 80)),
    LibraryStatus.playing: (0.25, (6, 9), (2, 40)),
    LibraryStatus.dropped: (0.15, (3, 6), (1, 15)),
    LibraryStatus.backlog: (0.20, None, (0, 0)),
}


@dataclass
class Summary:
    created_users: list[str] = field(default_factory=list)
    skipped_users: list[str] = field(default_factory=list)
    entries: int = 0
    follows: int = 0


def _pick_status(rng: random.Random) -> LibraryStatus:
    statuses = list(STATUS_PROFILE)
    weights = [STATUS_PROFILE[s][0] for s in statuses]
    return rng.choices(statuses, weights=weights, k=1)[0]


async def _collect_games(persona: Persona, game_source: GameSource, rng: random.Random) -> list[RawgGame]:
    pool: dict[int, RawgGame] = {}
    for slug in persona.genres:
        try:
            for game in await game_source(slug):
                pool.setdefault(game.rawg_id, game)
        except Exception:  # noqa: BLE001 — one bad genre shouldn't sink the bot
            continue
    games = list(pool.values())
    rng.shuffle(games)
    return games[: rng.randint(MIN_GAMES, MAX_GAMES)]


async def seed(
    session: AsyncSession,
    *,
    game_source: GameSource,
    password: str,
    rng: random.Random | None = None,
    now: datetime | None = None,
) -> Summary:
    rng = rng or random.Random()
    now = now or datetime.now(timezone.utc)
    summary = Summary()
    hashed = hash_password(password)
    bots: list[User] = []
    new_bots: list[User] = []

    for persona in PERSONAS:
        existing = (
            await session.exec(select(User).where(User.username == persona.username))
        ).first()
        if existing is not None:
            summary.skipped_users.append(persona.username)
            bots.append(existing)
            continue

        user = User(
            username=persona.username,
            email=f"bot_{persona.username}@{BOT_EMAIL_DOMAIN}",
            hashed_password=hashed,
            created_at=now - timedelta(days=ACTIVITY_WINDOW_DAYS + rng.randint(5, 60)),
        )
        session.add(user)
        await session.flush()

        for game in await _collect_games(persona, game_source, rng):
            db_game = await upsert_game_from_rawg(session, game)
            status = _pick_status(rng)
            _, rating_range, hours_range = STATUS_PROFILE[status]

            updated = now - timedelta(days=rng.uniform(0, ACTIVITY_WINDOW_DAYS))
            created = updated - timedelta(days=rng.uniform(0, 3))
            session.add(
                LibraryEntry(
                    user_id=user.id,
                    game_id=db_game.id,
                    status=status,
                    rating=rng.randint(*rating_range) if rating_range else None,
                    review_text=rng.choice(REVIEWS) if rng.random() < REVIEW_CHANCE else None,
                    hours_played=round(rng.uniform(*hours_range), 1),
                    source=LibrarySource.manual,
                    created_at=created,
                    updated_at=updated,
                )
            )
            summary.entries += 1

        await session.commit()
        await session.refresh(user)
        summary.created_users.append(persona.username)
        bots.append(user)
        new_bots.append(user)

    # Bots follow each other a little so their profiles aren't all zeros.
    # Only *new* bots get edges — otherwise every re-run would keep adding
    # fresh random follows and the script wouldn't be idempotent.
    for bot in new_bots:
        others = [b for b in bots if b.id != bot.id]
        for target in rng.sample(others, k=min(FOLLOWS_PER_BOT, len(others))):
            if await session.get(Follow, (bot.id, target.id)) is None:
                session.add(Follow(follower_id=bot.id, followed_id=target.id))
                summary.follows += 1
    await session.commit()
    return summary


async def main() -> None:
    from app.core.db import async_session_maker
    from app.services import rawg

    password = os.environ.get("BOT_PASSWORD") or secrets.token_urlsafe(12)

    async def from_rawg(slug: str) -> list[RawgGame]:
        return await rawg.discover_games(limit=25, ordering="-added", genres=slug)

    async with async_session_maker() as session:
        summary = await seed(session, game_source=from_rawg, password=password)

    print(f"created users : {summary.created_users or '-'}")
    print(f"skipped users : {summary.skipped_users or '-'}")
    print(f"library rows  : {summary.entries}")
    print(f"follow edges  : {summary.follows}")
    if summary.created_users:
        print(f"\nbot password  : {password}")
        print("(log in with any bot's username; set BOT_PASSWORD to choose it yourself)")


if __name__ == "__main__":
    asyncio.run(main())
