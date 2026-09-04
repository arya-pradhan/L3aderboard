"""Library CRUD + game search tests. RAWG is mocked so tests stay offline."""
from __future__ import annotations

from datetime import date

import pytest
from httpx import AsyncClient

from app.schemas.game import RawgGame
from app.services import rawg

HOLLOW_KNIGHT = RawgGame(
    rawg_id=9743,
    title="Hollow Knight",
    genres=["Platformer", "Indie", "Action"],
    tags=["Singleplayer", "Metroidvania"],
    platforms=["PC", "Nintendo Switch"],
    cover_url="https://media.rawg.io/hk.jpg",
    release_date=date(2017, 2, 23),
)
CELESTE = RawgGame(
    rawg_id=5,
    title="Celeste",
    genres=["Platformer", "Indie"],
    tags=["Singleplayer", "Difficult"],
    platforms=["PC"],
    cover_url="https://media.rawg.io/celeste.jpg",
    release_date=date(2018, 1, 25),
)


async def _register_and_auth(client: AsyncClient, username: str) -> dict[str, str]:
    await client.post(
        "/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "supersecret123",
        },
    )
    resp = await client.post(
        "/auth/login",
        data={"username": f"{username}@example.com", "password": "supersecret123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_rawg(monkeypatch: pytest.MonkeyPatch):
    games = {9743: HOLLOW_KNIGHT, 5: CELESTE}

    async def fake_get_game(rawg_id: int) -> RawgGame:
        if rawg_id not in games:
            raise rawg.RAWGNotFound(f"RAWG game {rawg_id} not found")
        return games[rawg_id]

    async def fake_search(query: str, *, limit: int = 10) -> list[RawgGame]:
        return [g for g in games.values() if query.lower() in g.title.lower()][:limit]

    monkeypatch.setattr(rawg, "get_game", fake_get_game)
    monkeypatch.setattr(rawg, "search_games", fake_search)


async def test_search_games(client: AsyncClient, mock_rawg) -> None:
    headers = await _register_and_auth(client, "searcher")
    resp = await client.get("/games/search", params={"q": "hollow"}, headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    assert body[0]["title"] == "Hollow Knight"
    assert body[0]["rawg_id"] == 9743


async def test_search_requires_auth(client: AsyncClient, mock_rawg) -> None:
    resp = await client.get("/games/search", params={"q": "hollow"})
    assert resp.status_code == 401


async def test_add_and_list_library(client: AsyncClient, mock_rawg) -> None:
    headers = await _register_and_auth(client, "ashley")

    add = await client.post(
        "/library", json={"rawg_id": 9743, "status": "playing"}, headers=headers
    )
    assert add.status_code == 201, add.text
    entry = add.json()
    assert entry["status"] == "playing"
    assert entry["source"] == "manual"
    assert entry["game"]["title"] == "Hollow Knight"
    assert entry["game"]["genres"] == ["Platformer", "Indie", "Action"]

    listing = await client.get("/library", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1


async def test_add_unknown_game_404(client: AsyncClient, mock_rawg) -> None:
    headers = await _register_and_auth(client, "unknown")
    resp = await client.post(
        "/library", json={"rawg_id": 999999}, headers=headers
    )
    assert resp.status_code == 404


async def test_duplicate_add_conflicts(client: AsyncClient, mock_rawg) -> None:
    headers = await _register_and_auth(client, "dup")
    await client.post("/library", json={"rawg_id": 9743}, headers=headers)
    resp = await client.post("/library", json={"rawg_id": 9743}, headers=headers)
    assert resp.status_code == 409


async def test_status_filter(client: AsyncClient, mock_rawg) -> None:
    headers = await _register_and_auth(client, "filt")
    await client.post(
        "/library", json={"rawg_id": 9743, "status": "playing"}, headers=headers
    )
    await client.post(
        "/library", json={"rawg_id": 5, "status": "backlog"}, headers=headers
    )

    playing = await client.get(
        "/library", params={"status": "playing"}, headers=headers
    )
    assert playing.status_code == 200
    titles = [e["game"]["title"] for e in playing.json()]
    assert titles == ["Hollow Knight"]


async def test_update_entry(client: AsyncClient, mock_rawg) -> None:
    headers = await _register_and_auth(client, "rater")
    add = await client.post(
        "/library", json={"rawg_id": 9743, "status": "playing"}, headers=headers
    )
    entry_id = add.json()["id"]

    patch = await client.patch(
        f"/library/{entry_id}",
        json={"status": "completed", "rating": 9, "review_text": "Sublime."},
        headers=headers,
    )
    assert patch.status_code == 200, patch.text
    body = patch.json()
    assert body["status"] == "completed"
    assert body["rating"] == 9
    assert body["review_text"] == "Sublime."


async def test_rating_out_of_range_rejected(client: AsyncClient, mock_rawg) -> None:
    headers = await _register_and_auth(client, "badrating")
    add = await client.post("/library", json={"rawg_id": 9743}, headers=headers)
    entry_id = add.json()["id"]
    resp = await client.patch(
        f"/library/{entry_id}", json={"rating": 11}, headers=headers
    )
    assert resp.status_code == 422


async def test_delete_entry(client: AsyncClient, mock_rawg) -> None:
    headers = await _register_and_auth(client, "deleter")
    add = await client.post("/library", json={"rawg_id": 9743}, headers=headers)
    entry_id = add.json()["id"]

    delete = await client.delete(f"/library/{entry_id}", headers=headers)
    assert delete.status_code == 204

    listing = await client.get("/library", headers=headers)
    assert listing.json() == []


async def test_cannot_touch_another_users_entry(
    client: AsyncClient, mock_rawg
) -> None:
    alice = await _register_and_auth(client, "alice")
    add = await client.post("/library", json={"rawg_id": 9743}, headers=alice)
    entry_id = add.json()["id"]

    bob = await _register_and_auth(client, "bob")
    patch = await client.patch(
        f"/library/{entry_id}", json={"status": "dropped"}, headers=bob
    )
    assert patch.status_code == 404
    delete = await client.delete(f"/library/{entry_id}", headers=bob)
    assert delete.status_code == 404
