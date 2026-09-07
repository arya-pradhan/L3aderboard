"""Aggregate API router. New route modules get included here as we add steps."""
from fastapi import APIRouter

from app.api.routes import (
    auth,
    discover,
    feed,
    games,
    library,
    recommendations,
    steam,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(steam.router)
api_router.include_router(games.router)
api_router.include_router(library.router)
api_router.include_router(users.router)
api_router.include_router(feed.router)
api_router.include_router(discover.router)
api_router.include_router(recommendations.router)
