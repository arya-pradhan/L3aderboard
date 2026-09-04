"""Follow system + activity feed tests. RAWG is mocked for library adds."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.schemas.game import RawgGame
from app.services import rawg

GAMES = {
    9743: RawgGame(rawg_id=9743, title="Hollow Knight", genres=["Indie"]),
    22121: RawgGame(rawg_id=22121, title="Celeste", genres=["Platformer"]),
    5: RawgGame(rawg_id=5, title="Portal 2", genres=["Puzzle"]),
}


@pytest.fixture
def mock_rawg(monkeypatch: pytest.MonkeyPatch):
    async def fake_get_game(rawg_id: int) -> RawgGame:
        if rawg_id not in GAMES:
            raise rawg.RAWGNotFound("nope")
        return GAMES[rawg_id]

    monkeypatch.setattr(rawg, "get_game", fake_get_game)


async def _auth(client: AsyncClient, username: str) -> dict[str, str]:
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
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _add_game(client, headers, rawg_id, status="playing"):
    return await client.post(
        "/library", json={"rawg_id": rawg_id, "status": status}, headers=headers
    )


# --- follow / unfollow ---------------------------------------------------


async def test_follow_and_profile_counts(client: AsyncClient) -> None:
    alice = await _auth(client, "alice")
    await _auth(client, "bob")

    follow = await client.post("/users/bob/follow", headers=alice)
    assert follow.status_code == 204

    # From alice's perspective, bob's profile shows the follow.
    bob_profile = (await client.get("/users/bob", headers=alice)).json()
    assert bob_profile["followers_count"] == 1
    assert bob_profile["is_following"] is True
    assert bob_profile["is_self"] is False

    # Alice's own following count went up.
    alice_profile = (await client.get("/users/alice", headers=alice)).json()
    assert alice_profile["following_count"] == 1
    assert alice_profile["is_self"] is True


async def test_follow_is_idempotent(client: AsyncClient) -> None:
    alice = await _auth(client, "alice")
    await _auth(client, "bob")
    assert (await client.post("/users/bob/follow", headers=alice)).status_code == 204
    assert (await client.post("/users/bob/follow", headers=alice)).status_code == 204
    bob = (await client.get("/users/bob", headers=alice)).json()
    assert bob["followers_count"] == 1  # not doubled


async def test_unfollow(client: AsyncClient) -> None:
    alice = await _auth(client, "alice")
    await _auth(client, "bob")
    await client.post("/users/bob/follow", headers=alice)
    assert (await client.delete("/users/bob/follow", headers=alice)).status_code == 204
    bob = (await client.get("/users/bob", headers=alice)).json()
    assert bob["followers_count"] == 0
    assert bob["is_following"] is False
    # Unfollowing when not following is still a no-op success.
    assert (await client.delete("/users/bob/follow", headers=alice)).status_code == 204


async def test_cannot_follow_self(client: AsyncClient) -> None:
    alice = await _auth(client, "alice")
    resp = await client.post("/users/alice/follow", headers=alice)
    assert resp.status_code == 400


async def test_follow_missing_user_404(client: AsyncClient) -> None:
    alice = await _auth(client, "alice")
    assert (await client.post("/users/ghost/follow", headers=alice)).status_code == 404
    assert (await client.get("/users/ghost", headers=alice)).status_code == 404


async def test_profile_games_count(client: AsyncClient, mock_rawg) -> None:
    alice = await _auth(client, "alice")
    await _add_game(client, alice, 9743)
    await _add_game(client, alice, 22121)
    profile = (await client.get("/users/alice", headers=alice)).json()
    assert profile["games_count"] == 2


async def test_view_another_users_library(client: AsyncClient, mock_rawg) -> None:
    alice = await _auth(client, "alice")
    bob = await _auth(client, "bob")
    await _add_game(client, bob, 9743, status="completed")
    await _add_game(client, bob, 22121, status="backlog")

    # Alice can view bob's public library, and filter it by status.
    full = (await client.get("/users/bob/library", headers=alice)).json()
    assert {e["game"]["title"] for e in full} == {"Hollow Knight", "Celeste"}

    completed = (
        await client.get("/users/bob/library", params={"status": "completed"}, headers=alice)
    ).json()
    assert [e["game"]["title"] for e in completed] == ["Hollow Knight"]

    # Unknown user -> 404.
    assert (await client.get("/users/ghost/library", headers=alice)).status_code == 404


# --- activity feed -------------------------------------------------------


async def test_feed_empty_without_follows(client: AsyncClient) -> None:
    alice = await _auth(client, "alice")
    resp = await client.get("/feed", headers=alice)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_feed_shows_followed_users(client: AsyncClient, mock_rawg) -> None:
    alice = await _auth(client, "alice")
    bob = await _auth(client, "bob")
    carol = await _auth(client, "carol")

    await client.post("/users/bob/follow", headers=alice)
    await _add_game(client, bob, 9743, status="completed")
    await _add_game(client, carol, 22121)  # carol is NOT followed

    feed = (await client.get("/feed", headers=alice)).json()
    assert len(feed) == 1
    item = feed[0]
    assert item["user"]["username"] == "bob"
    assert item["game"]["title"] == "Hollow Knight"
    assert item["status"] == "completed"


async def test_feed_ordered_by_recency(client: AsyncClient, mock_rawg) -> None:
    alice = await _auth(client, "alice")
    bob = await _auth(client, "bob")
    await client.post("/users/bob/follow", headers=alice)

    add_a = await _add_game(client, bob, 9743)  # Hollow Knight
    await _add_game(client, bob, 22121)  # Celeste (added second)

    # Touch Hollow Knight so it becomes the most recently updated entry.
    entry_a = add_a.json()["id"]
    await client.patch(
        f"/library/{entry_a}", json={"status": "completed"}, headers=bob
    )

    feed = (await client.get("/feed", headers=alice)).json()
    titles = [i["game"]["title"] for i in feed]
    assert titles == ["Hollow Knight", "Celeste"]
