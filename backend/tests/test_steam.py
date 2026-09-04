"""Steam OpenID sign-in + library import tests. All network calls are mocked."""
from __future__ import annotations

from urllib.parse import urlparse

import pytest
from httpx import AsyncClient

from app.schemas.game import RawgGame
from app.schemas.steam import SteamGame
from app.services import rawg, steam
from app.services.steam import STEAM_OPENID_URL, SteamNotConfigured

STEAM_ID = "76561198000000000"


def _token_from_redirect(location: str) -> str:
    fragment = urlparse(location).fragment  # access_token=...&token_type=bearer
    parts = dict(p.split("=", 1) for p in fragment.split("&"))
    return parts["access_token"]


async def _steam_signin(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, *, persona: str | None
) -> dict[str, str]:
    async def fake_verify(params: dict[str, str]) -> str:
        return STEAM_ID

    async def fake_persona(steam_id: str) -> str | None:
        return persona

    monkeypatch.setattr(steam, "verify_openid", fake_verify)
    monkeypatch.setattr(steam, "get_persona_name", fake_persona)

    resp = await client.get("/auth/steam/callback", params={"openid.mode": "id_res"})
    assert resp.status_code in (302, 307), resp.text
    token = _token_from_redirect(resp.headers["location"])
    return {"Authorization": f"Bearer {token}"}


def test_build_login_url() -> None:
    url = steam.build_login_url("http://test/cb", "http://test/")
    assert url.startswith(STEAM_OPENID_URL)
    assert "openid.mode=checkid_setup" in url
    assert "identifier_select" in url


async def test_steam_login_redirects(client: AsyncClient) -> None:
    resp = await client.get("/auth/steam/login")
    assert resp.status_code in (302, 307)
    assert resp.headers["location"].startswith(STEAM_OPENID_URL)


async def test_steam_callback_creates_user(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _steam_signin(client, monkeypatch, persona="Ashley Plays")
    me = await client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    body = me.json()
    assert body["steam_id"] == STEAM_ID
    assert body["email"] is None
    assert body["username"] == "AshleyPlays"  # sanitized persona


async def test_steam_callback_is_idempotent(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    h1 = await _steam_signin(client, monkeypatch, persona="Ashley")
    h2 = await _steam_signin(client, monkeypatch, persona="Ashley")
    id1 = (await client.get("/auth/me", headers=h1)).json()["id"]
    id2 = (await client.get("/auth/me", headers=h2)).json()["id"]
    assert id1 == id2  # same SteamID -> same account, not a duplicate


async def test_import_requires_linked_steam(client: AsyncClient) -> None:
    # A plain email/password user has no steam_id.
    await client.post(
        "/auth/register",
        json={"username": "noSteam", "email": "n@e.com", "password": "supersecret1"},
    )
    login = await client.post(
        "/auth/login", data={"username": "n@e.com", "password": "supersecret1"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    resp = await client.post("/library/steam/import", headers=headers)
    assert resp.status_code == 400


async def test_import_without_key_returns_503(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _steam_signin(client, monkeypatch, persona="keyless")

    async def raise_not_configured(steam_id: str):
        raise SteamNotConfigured("STEAM_API_KEY is not configured.")

    monkeypatch.setattr(steam, "get_owned_games", raise_not_configured)
    resp = await client.post("/library/steam/import", headers=headers)
    assert resp.status_code == 503


async def test_import_success(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await _steam_signin(client, monkeypatch, persona="importer")

    owned = [
        SteamGame(appid=367520, name="Hollow Knight", playtime_minutes=1500),
        SteamGame(appid=504230, name="Celeste", playtime_minutes=600),
        SteamGame(appid=999999, name="Totally Obscure Game", playtime_minutes=30),
    ]

    async def fake_owned(steam_id: str) -> list[SteamGame]:
        return owned

    async def fake_search(query: str, *, limit: int = 10) -> list[RawgGame]:
        known = {
            "Hollow Knight": RawgGame(rawg_id=9743, title="Hollow Knight",
                                      genres=["Indie"], tags=["Metroidvania"]),
            "Celeste": RawgGame(rawg_id=22121, title="Celeste", genres=["Platformer"]),
        }
        return [known[query]] if query in known else []

    monkeypatch.setattr(steam, "get_owned_games", fake_owned)
    monkeypatch.setattr(rawg, "search_games", fake_search)

    resp = await client.post("/library/steam/import", headers=headers)
    assert resp.status_code == 200, resp.text
    summary = resp.json()
    assert summary["total_owned"] == 3
    assert summary["created"] == 3
    assert summary["matched_rawg"] == 2
    assert summary["unmatched"] == 1

    # Library now holds all three, marked as Steam imports with playtime.
    lib = (await client.get("/library", headers=headers)).json()
    assert len(lib) == 3
    hk = next(e for e in lib if e["game"]["title"] == "Hollow Knight")
    assert hk["source"] == "steam_import"
    assert hk["hours_played"] == 25.0  # 1500 min / 60

    # Re-import refreshes playtime instead of duplicating.
    owned[0].playtime_minutes = 1800
    resp2 = await client.post("/library/steam/import", headers=headers)
    summary2 = resp2.json()
    assert summary2["created"] == 0
    assert summary2["updated"] == 3
    lib2 = (await client.get("/library", headers=headers)).json()
    assert len(lib2) == 3
    hk2 = next(e for e in lib2 if e["game"]["title"] == "Hollow Knight")
    assert hk2["hours_played"] == 30.0
