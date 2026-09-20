"""GET /users/suggested — people to follow."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.schemas.game import RawgGame
from app.services import rawg


@pytest.fixture
def mock_rawg(monkeypatch: pytest.MonkeyPatch):
    async def fake_get_game(rawg_id: int) -> RawgGame:
        return RawgGame(rawg_id=rawg_id, title=f"Game {rawg_id}", genres=["Indie"])

    monkeypatch.setattr(rawg, "get_game", fake_get_game)


async def _auth(client: AsyncClient, username: str) -> dict[str, str]:
    await client.post(
        "/auth/register",
        json={"username": username, "email": f"{username}@e.com", "password": "supersecret1"},
    )
    r = await client.post(
        "/auth/login", data={"username": f"{username}@e.com", "password": "supersecret1"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_route_is_not_shadowed_by_username(client: AsyncClient) -> None:
    """'suggested' must resolve to the endpoint, not to a user named 'suggested'."""
    me = await _auth(client, "myself")
    resp = await client.get("/users/suggested", headers=me)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_excludes_self_and_followed_and_orders_by_library_size(
    client: AsyncClient, mock_rawg
) -> None:
    me = await _auth(client, "myself")
    big = await _auth(client, "biglib")
    small = await _auth(client, "smalllib")
    await _auth(client, "followed")

    for i in range(3):
        await client.post("/library", json={"rawg_id": 100 + i}, headers=big)
    await client.post("/library", json={"rawg_id": 200}, headers=small)

    await client.post("/users/followed/follow", headers=me)

    rows = (await client.get("/users/suggested", headers=me)).json()
    names = [r["username"] for r in rows]

    assert "myself" not in names
    assert "followed" not in names
    assert names[:2] == ["biglib", "smalllib"]  # biggest library first
    assert rows[0]["games_count"] == 3
    assert rows[1]["games_count"] == 1


async def test_respects_limit(client: AsyncClient) -> None:
    me = await _auth(client, "myself")
    for i in range(5):
        await _auth(client, f"other{i}")
    rows = (await client.get("/users/suggested?limit=2", headers=me)).json()
    assert len(rows) == 2
