"""Steam OpenID sign-in / account-linking routes.

`GET /auth/steam/login`   -> redirects the user to Steam to authenticate.
`GET /auth/steam/callback`-> verifies the response, finds-or-creates the user,
                             and redirects to the frontend with a JWT.

This is the Steam signup/login path: a verified SteamID maps to a GamerLog user
(created on first sign-in). It needs no Steam Web API key.
"""
from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlmodel import select

from app.core.config import settings
from app.core.deps import SessionDep
from app.core.security import create_access_token
from app.models import User
from app.services import steam
from app.services.steam import SteamError

router = APIRouter(prefix="/auth/steam", tags=["auth", "steam"])


async def _unique_username(session: SessionDep, base: str, steam_id: str) -> str:
    """Derive a unique username from a Steam persona name."""
    cleaned = re.sub(r"[^A-Za-z0-9_]", "", base or "")[:40]
    candidate = cleaned or f"steam_{steam_id}"

    suffix = 0
    while True:
        name = candidate if suffix == 0 else f"{candidate}_{suffix}"
        exists = (
            await session.exec(select(User).where(User.username == name))
        ).first()
        if exists is None:
            return name
        suffix += 1


@router.get("/login")
async def steam_login(request: Request) -> RedirectResponse:
    return_to = str(request.url_for("steam_callback"))
    realm = str(request.base_url)
    return RedirectResponse(steam.build_login_url(return_to, realm))


@router.get("/callback", name="steam_callback")
async def steam_callback(request: Request, session: SessionDep) -> RedirectResponse:
    params = dict(request.query_params)
    try:
        steam_id = await steam.verify_openid(params)
    except SteamError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    if not steam_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Steam authentication failed or was cancelled",
        )

    user = (
        await session.exec(select(User).where(User.steam_id == steam_id))
    ).first()
    if user is None:
        persona = await steam.get_persona_name(steam_id)
        username = await _unique_username(session, persona or "", steam_id)
        user = User(username=username, email=None, steam_id=steam_id)
        session.add(user)
        await session.commit()
        await session.refresh(user)

    token = create_access_token(subject=user.id)
    # Token in the URL fragment: it isn't sent to servers or logged like a query.
    redirect = f"{settings.frontend_url}/auth/steam#access_token={token}&token_type=bearer"
    return RedirectResponse(redirect)
