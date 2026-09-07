"""Home-page discovery rows. RAWG is mocked so tests stay offline."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.schemas.game import RawgGame
from app.services import rawg

GENRES = [
    {"slug": "indie", "name": "Indie"},
    {"slug": "platformer", "name": "Platformer"},
    {"slug": "action", "name": "Action"},
]

HOLLOW_KNIGHT = RawgGame(
    rawg_id=1, title="Hollow Knight", genres=["Indie", "Platformer"]
)


async def _auth(client: AsyncClient, username: str) -> dict[str, str]:
    await client.post(
        "/auth/register",
        json={"username": username, "email": f"{username}@e.com", "password": "supersecret1"},
    )
    r = await client.post(
        "/auth/login", data={"username": f"{username}@e.com", "password": "supersecret1"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def mock_rawg(monkeypatch: pytest.MonkeyPatch):
    calls: list[dict] = []

    async def fake_discover(*, limit: int = 20, **filters) -> list[RawgGame]:
        calls.append(filters)
        return [RawgGame(rawg_id=100 + len(calls), title=f"Game {len(calls)}")]

    async def fake_list_genres() -> list[dict[str, str]]:
        return GENRES

    async def fake_get_game(rawg_id: int) -> RawgGame:
        return HOLLOW_KNIGHT

    monkeypatch.setattr(rawg, "discover_games", fake_discover)
    monkeypatch.setattr(rawg, "list_genres", fake_list_genres)
    monkeypatch.setattr(rawg, "get_game", fake_get_game)
    return calls


async def test_home_rows_shape(client: AsyncClient, mock_rawg) -> None:
    headers = await _auth(client, "browser")
    resp = await client.get("/discover/home", headers=headers)
    assert resp.status_code == 200, resp.text
    rows = resp.json()

    keys = [r["key"] for r in rows]
    assert "popular" in keys
    assert "upcoming" in keys
    # Empty library -> default genre rows.
    assert "genre:indie" in keys
    assert all(r["games"] for r in rows)
    assert all("title" in r and "subtitle" in r for r in rows)


async def test_home_requires_auth(client: AsyncClient, mock_rawg) -> None:
    assert (await client.get("/discover/home")).status_code == 401


async def test_genre_rows_follow_library(client: AsyncClient, mock_rawg) -> None:
    headers = await _auth(client, "platformerfan")
    # Library game is Indie/Platformer -> those genres should drive the rows.
    await client.post("/library", json={"rawg_id": 1}, headers=headers)

    rows = (await client.get("/discover/home", headers=headers)).json()
    keys = [r["key"] for r in rows]
    assert "genre:indie" in keys
    assert "genre:platformer" in keys


async def test_failing_row_is_dropped_not_fatal(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One bad upstream row shouldn't 500 the whole home page."""
    calls = {"n": 0}

    async def flaky_discover(*, limit: int = 20, **filters) -> list[RawgGame]:
        calls["n"] += 1
        if calls["n"] == 1:
            raise rawg.RAWGError("upstream blew up")
        return [RawgGame(rawg_id=7, title="Survivor")]

    async def fake_list_genres() -> list[dict[str, str]]:
        return GENRES

    monkeypatch.setattr(rawg, "discover_games", flaky_discover)
    monkeypatch.setattr(rawg, "list_genres", fake_list_genres)

    headers = await _auth(client, "resilient")
    resp = await client.get("/discover/home", headers=headers)
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) >= 1  # the failing row is simply absent
    assert all(r["games"] for r in rows)
