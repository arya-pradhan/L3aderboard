"""Backlog assistant: one DeepSeek call grounded in the user's library.

Stateless — the frontend sends the whole (short) conversation each time. The
user's library and current recommendations go into the system prompt, so no
tool loop is needed.
"""
# NOTE: no `from __future__ import annotations` — see auth.py; slowapi's
# wrapper breaks FastAPI's resolution of string-typed dependencies.
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlmodel import select

from app.api.routes.recommendations import get_recommendations
from app.core.config import settings
from app.core.deps import CurrentUser, SessionDep
from app.core.ratelimit import CHAT_LIMIT, limiter, user_or_ip
from app.models import Game, LibraryEntry

router = APIRouter(tags=["chat"])

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
MAX_LIBRARY_LINES = 300  # ponytail: hard cap; summarize or add tools if libraries grow past this

SYSTEM_PROMPT = """You are the L3aderboard assistant, a friendly gaming buddy.
Help the user work through their backlog, decide what to play next, and find
new games they'd enjoy. Ground your answers in their library and the
recommendations below. Only suggest games from those lists or games you are
confident really exist. Keep replies short and conversational.

## Their library (title | status | rating/10 | hours | genres)
{library}

## Recommended for them (not yet in their library)
{recs}"""


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)


class ChatReply(BaseModel):
    reply: str


async def _build_system_prompt(user, session) -> str:
    rows = (
        await session.exec(
            select(LibraryEntry, Game)
            .join(Game, Game.id == LibraryEntry.game_id)
            .where(LibraryEntry.user_id == user.id)
            .order_by(LibraryEntry.updated_at.desc())
            .limit(MAX_LIBRARY_LINES)
        )
    ).all()
    library = "\n".join(
        f"- {g.title} | {e.status.value} | {e.rating or '-'} | {e.hours_played:g} | "
        f"{', '.join(g.genres or [])}"
        for e, g in rows
    ) or "(empty — they haven't added any games yet)"

    recs = await get_recommendations(user, session, limit=10)
    rec_text = "\n".join(
        f"- {r.title} ({', '.join(r.genres)})" for r in recs
    ) or "(none available)"
    return SYSTEM_PROMPT.format(library=library, recs=rec_text)


async def _complete(messages: list[dict]) -> str:
    """Call DeepSeek's OpenAI-compatible chat endpoint."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            DEEPSEEK_URL,
            headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
            json={"model": settings.deepseek_model, "messages": messages},
        )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


@router.post("/chat", response_model=ChatReply)
@limiter.limit(CHAT_LIMIT, key_func=user_or_ip)
async def chat(
    request: Request, body: ChatRequest, current_user: CurrentUser, session: SessionDep
) -> ChatReply:
    if not settings.deepseek_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The assistant isn't configured (DEEPSEEK_API_KEY missing).",
        )
    system = await _build_system_prompt(current_user, session)
    messages = [{"role": "system", "content": system}] + [
        m.model_dump() for m in body.messages
    ]
    try:
        reply = await _complete(messages)
    except (httpx.HTTPError, KeyError, IndexError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The assistant is unavailable right now — try again in a bit.",
        )
    return ChatReply(reply=reply)
