"""Steam integration.

Two independent concerns live here:

1. **OpenID sign-in** (`build_login_url`, `verify_openid`) — Steam's OpenID 2.0
   flow. This does NOT require a Steam Web API key, so linking/sign-in works
   before a key is configured.
2. **Web API reads** (`get_owned_games`, `get_persona_name`) — these DO require
   `STEAM_API_KEY`; they raise `SteamNotConfigured` until one is set.
"""
from __future__ import annotations

import re
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.schemas.steam import SteamGame

STEAM_OPENID_URL = "https://steamcommunity.com/openid/login"
STEAM_API_BASE = "https://api.steampowered.com"
_OPENID_NS = "http://specs.openid.net/auth/2.0"
_IDENTIFIER_SELECT = "http://specs.openid.net/auth/2.0/identifier_select"
_STEAMID_RE = re.compile(r"^https://steamcommunity\.com/openid/id/(\d+)$")
_TIMEOUT = httpx.Timeout(10.0)


class SteamError(RuntimeError):
    """Generic upstream/transport error talking to Steam."""


class SteamNotConfigured(SteamError):
    """STEAM_API_KEY is not set (only needed for Web API reads)."""


def _require_key() -> str:
    if not settings.steam_api_key:
        raise SteamNotConfigured(
            "STEAM_API_KEY is not configured. Add it to the backend .env."
        )
    return settings.steam_api_key


# --- OpenID sign-in (no API key required) --------------------------------


def build_login_url(return_to: str, realm: str) -> str:
    """Build the Steam OpenID redirect URL the user is sent to."""
    params = {
        "openid.ns": _OPENID_NS,
        "openid.mode": "checkid_setup",
        "openid.return_to": return_to,
        "openid.realm": realm,
        "openid.identity": _IDENTIFIER_SELECT,
        "openid.claimed_id": _IDENTIFIER_SELECT,
    }
    return f"{STEAM_OPENID_URL}?{urlencode(params)}"


async def verify_openid(params: dict[str, str]) -> str | None:
    """Verify the OpenID callback params with Steam.

    Returns the 64-bit SteamID on success, else None. Does not need an API key.
    """
    if params.get("openid.mode") != "id_res":
        return None

    data = dict(params)
    data["openid.mode"] = "check_authentication"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(STEAM_OPENID_URL, data=data)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise SteamError(f"Steam OpenID verification failed: {exc}") from exc

    if "is_valid:true" not in resp.text:
        return None

    match = _STEAMID_RE.match(params.get("openid.claimed_id", ""))
    return match.group(1) if match else None


# --- Web API reads (API key required) ------------------------------------


async def get_owned_games(steam_id: str) -> list[SteamGame]:
    """Fetch a user's owned games + playtime via GetOwnedGames."""
    key = _require_key()
    params = {
        "key": key,
        "steamid": steam_id,
        "include_appinfo": "true",
        "include_played_free_games": "true",
        "format": "json",
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{STEAM_API_BASE}/IPlayerService/GetOwnedGames/v1/", params=params
            )
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise SteamError(f"Steam GetOwnedGames failed: {exc}") from exc

    games = resp.json().get("response", {}).get("games", []) or []
    return [
        SteamGame(
            appid=g["appid"],
            name=g.get("name") or f"App {g['appid']}",
            playtime_minutes=g.get("playtime_forever", 0),
        )
        for g in games
    ]


async def get_persona_name(steam_id: str) -> str | None:
    """Best-effort display name via GetPlayerSummaries. None on any failure."""
    try:
        key = _require_key()
    except SteamNotConfigured:
        return None
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{STEAM_API_BASE}/ISteamUser/GetPlayerSummaries/v2/",
                params={"key": key, "steamids": steam_id},
            )
            resp.raise_for_status()
        players = resp.json().get("response", {}).get("players", [])
        return players[0].get("personaname") if players else None
    except (httpx.HTTPError, KeyError, IndexError):
        return None
