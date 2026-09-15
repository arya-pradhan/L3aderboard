"""Rate limiting (slowapi).

Protects the public deployment from the three realistic abuse cases: login
brute-force, registration spam, and burning the RAWG quota via search.
"""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from app.core.security import decode_access_token


def client_ip(request: Request) -> str:
    """The real client IP.

    Railway terminates TLS at its edge proxy, so `request.client.host` is the
    proxy — keying on it would make every user share a single limit. The real
    client is the first hop of X-Forwarded-For, which Railway sets.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def user_or_ip(request: Request) -> str:
    """Per-user key for authenticated routes, falling back to IP."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        sub = decode_access_token(auth[7:].strip())
        if sub:
            return f"user:{sub}"
    return f"ip:{client_ip(request)}"


limiter = Limiter(key_func=client_ip)

# Limits are expressed once here so they're easy to find and tune.
LOGIN_LIMIT = "5/minute"        # per IP — brute-force protection
REGISTER_LIMIT = "3/hour"       # per IP — account-spam protection
SEARCH_LIMIT = "30/minute"      # per user — RAWG quota protection (uncached)
DETAIL_LIMIT = "60/minute"      # per user — RAWG quota protection (uncached)


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    # Use a `detail` field so the frontend's error surface shows it verbatim.
    return JSONResponse(
        status_code=429,
        content={"detail": f"Too many requests — slow down (limit: {exc.detail})."},
    )
