"""FastAPI application entrypoint for GamerLog."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.api.router import api_router
from app.core.config import settings
from app.core.ratelimit import limiter, rate_limit_handler
from app.services.rawg import RAWGError, RAWGNotConfigured, RAWGNotFound
from app.services.steam import SteamError, SteamNotConfigured

app = FastAPI(
    title="GamerLog API",
    version="0.1.0",
    description="A MyAnimeList-style social gaming profile & recommendation app.",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# Upstream (RAWG/Steam) failures -> HTTP, once for every route.
_UPSTREAM_STATUS = {RAWGNotConfigured: 503, RAWGNotFound: 404, SteamNotConfigured: 503}


async def upstream_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=_UPSTREAM_STATUS.get(type(exc), 502), content={"detail": str(exc)}
    )


app.add_exception_handler(RAWGError, upstream_error_handler)
app.add_exception_handler(SteamError, upstream_error_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
