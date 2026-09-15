"""Rate limiting. The limiter is disabled suite-wide (conftest); these tests
switch it on and reset its counters so each starts from a clean slate."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.ratelimit import client_ip, limiter
from app.schemas.game import RawgGame
from app.services import rawg


@pytest.fixture
def limits_on():
    limiter.enabled = True
    limiter.reset()
    yield
    limiter.reset()
    limiter.enabled = False


def _reg(i: int) -> dict:
    return {"username": f"user{i}", "email": f"user{i}@e.com", "password": "supersecret1"}


async def _login(client: AsyncClient, email: str) -> dict[str, str]:
    r = await client.post("/auth/login", data={"username": email, "password": "supersecret1"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# --- login: 5/minute per IP ----------------------------------------------


async def test_login_brute_force_is_throttled(client: AsyncClient, limits_on) -> None:
    for _ in range(5):
        r = await client.post(
            "/auth/login", data={"username": "nobody@e.com", "password": "wrong"}
        )
        assert r.status_code == 401  # wrong creds, but still allowed through

    r = await client.post("/auth/login", data={"username": "nobody@e.com", "password": "wrong"})
    assert r.status_code == 429
    assert "Too many requests" in r.json()["detail"]


# --- register: 3/hour per IP ---------------------------------------------


async def test_registration_spam_is_throttled(client: AsyncClient, limits_on) -> None:
    for i in range(3):
        assert (await client.post("/auth/register", json=_reg(i))).status_code == 201
    assert (await client.post("/auth/register", json=_reg(99))).status_code == 429


# --- search: 30/minute per user (not per IP) -----------------------------


async def test_search_is_throttled_per_user(
    client: AsyncClient, limits_on, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_search(query: str, *, limit: int = 10) -> list[RawgGame]:
        return [RawgGame(rawg_id=1, title="x")]

    monkeypatch.setattr(rawg, "search_games", fake_search)

    await client.post("/auth/register", json=_reg(1))
    await client.post("/auth/register", json=_reg(2))
    alice = await _login(client, "user1@e.com")
    bob = await _login(client, "user2@e.com")

    for _ in range(30):
        assert (await client.get("/games/search?q=x", headers=alice)).status_code == 200
    assert (await client.get("/games/search?q=x", headers=alice)).status_code == 429

    # Same IP, different user: bob is unaffected — the key is the user, not the IP.
    assert (await client.get("/games/search?q=x", headers=bob)).status_code == 200


# --- proxy-aware IP keying ------------------------------------------------


def test_client_ip_prefers_forwarded_header() -> None:
    """Behind Railway's proxy, X-Forwarded-For carries the real client."""

    class Req:
        def __init__(self, headers, host):
            self.headers = headers
            self.client = type("C", (), {"host": host})()

    behind_proxy = Req({"x-forwarded-for": "203.0.113.9, 10.0.0.1"}, "10.0.0.1")
    assert client_ip(behind_proxy) == "203.0.113.9"

    direct = Req({}, "198.51.100.4")
    assert client_ip(direct) == "198.51.100.4"


async def test_limits_are_disabled_by_default_in_suite(client: AsyncClient) -> None:
    """Sanity check that the conftest switch works, so other tests aren't
    silently throttled."""
    for _ in range(7):
        r = await client.post("/auth/login", data={"username": "n@e.com", "password": "w"})
        assert r.status_code == 401
