"""Recommender unit tests + endpoint integration test."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.schemas.game import RawgGame
from app.services import rawg
from app.services.recommender import (
    CandidateItem,
    LikedItem,
    extract_features,
    recommend,
)

# --- pure unit tests -----------------------------------------------------


def test_extract_features_normalizes():
    assert extract_features(["Action RPG", "Indie"], ["Open World"]) == [
        "action_rpg",
        "indie",
        "open_world",
    ]
    assert extract_features(None, None) == []


def test_recommend_ranks_similar_first():
    liked = [LikedItem(extract_features(["Indie", "Platformer"], ["Metroidvania"]), 9)]
    candidates = [
        CandidateItem(2, extract_features(["Indie", "Platformer"], ["Difficult"])),
        CandidateItem(3, extract_features(["Shooter", "Action"], ["Gore"])),
    ]
    result = recommend(liked, candidates)
    # The platformer shares genres; the shooter shares nothing (score 0, dropped).
    assert result[0].key == 2
    assert result[0].score > 0
    assert 3 not in [r.key for r in result]


def test_recommend_empty_inputs():
    liked = [LikedItem(["indie"], 1)]
    cand = [CandidateItem(1, ["indie"])]
    assert recommend([], cand) == []
    assert recommend(liked, []) == []
    assert recommend([LikedItem([], 1)], cand) == []  # no usable features


# --- endpoint integration ------------------------------------------------

GAMES = {
    1: RawgGame(rawg_id=1, title="Hollow Knight", genres=["Indie", "Platformer"], tags=["Metroidvania"]),
    2: RawgGame(rawg_id=2, title="Celeste", genres=["Indie", "Platformer"], tags=["Difficult"]),
    3: RawgGame(rawg_id=3, title="Doom", genres=["Shooter", "Action"], tags=["Gore"]),
}

GENRES = [
    {"slug": "indie", "name": "Indie"},
    {"slug": "platformer", "name": "Platformer"},
    {"slug": "shooter", "name": "Shooter"},
]


@pytest.fixture
def mock_rawg(monkeypatch: pytest.MonkeyPatch):
    """Mock the whole RAWG surface the recommender touches."""

    async def fake_get_game(rawg_id: int) -> RawgGame:
        return GAMES[rawg_id]

    async def fake_list_genres() -> list[dict[str, str]]:
        return GENRES

    async def fake_discover(*, limit: int = 20, **filters) -> list[RawgGame]:
        # The candidate pool RAWG would return for the user's top genres.
        # Includes the already-owned game to prove it gets excluded.
        return [GAMES[1], GAMES[2], GAMES[3]]

    monkeypatch.setattr(rawg, "get_game", fake_get_game)
    monkeypatch.setattr(rawg, "list_genres", fake_list_genres)
    monkeypatch.setattr(rawg, "discover_games", fake_discover)


async def _auth(client: AsyncClient, username: str) -> dict[str, str]:
    await client.post(
        "/auth/register",
        json={"username": username, "email": f"{username}@e.com", "password": "supersecret1"},
    )
    r = await client.post(
        "/auth/login", data={"username": f"{username}@e.com", "password": "supersecret1"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_recommendations_endpoint(client: AsyncClient, mock_rawg) -> None:
    arya = await _auth(client, "arya")

    # arya rates a platformer highly — that alone should be enough now that
    # candidates come from RAWG rather than the local catalog.
    await client.post(
        "/library", json={"rawg_id": 1, "status": "completed", "rating": 9}, headers=arya
    )

    recs = (await client.get("/recommendations", headers=arya)).json()
    titles = [g["title"] for g in recs]
    assert titles[:1] == ["Celeste"]  # similar game ranked first
    assert "Doom" not in titles  # nothing in common -> not recommended
    assert "Hollow Knight" not in titles  # already owned, excluded from pool


async def test_recommendations_need_no_other_users(
    client: AsyncClient, mock_rawg
) -> None:
    """The whole point of the RAWG-sourced pool: a solo user gets results."""
    solo = await _auth(client, "solo")
    await client.post(
        "/library", json={"rawg_id": 1, "status": "completed", "rating": 8}, headers=solo
    )
    recs = (await client.get("/recommendations", headers=solo)).json()
    assert len(recs) > 0


async def test_recommendations_empty_for_new_user(client: AsyncClient) -> None:
    new = await _auth(client, "newbie")
    assert (await client.get("/recommendations", headers=new)).json() == []
