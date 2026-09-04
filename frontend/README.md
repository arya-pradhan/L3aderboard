# GamerLog — Frontend (Vite + React)

Single-page app for GamerLog / L3aderboard, styled to the approved mockups and
wired to the FastAPI backend.

## Setup

```bash
cd frontend
npm install
cp .env.example .env   # set VITE_API_URL to your backend (default http://127.0.0.1:8000)
npm run dev            # http://localhost:5173
```

The backend must be running (see `../backend/README.md`) and its `CORS_ORIGINS`
must include the dev origin (`http://localhost:5173`, already the default).

## Routes
- `/login`, `/register` — email/password auth, plus "Continue with Steam"
- `/auth/steam` — Steam OpenID callback (reads the token from the URL fragment)
- `/` — Discover: search RAWG and add games to your library
- `/library` — your library: stat band, status filters, edit/rate/review, Steam sync
- `/u/:username` — public profile: follow, stats, their library
- `/feed` — recent activity from people you follow

## Notes
Screens map to what the API supports. Mockup features without a backend
(collections, top-4, Twitch, cross-user review lists, editorial rows) are
intentionally omitted.

## Build
```bash
npm run build     # outputs to dist/ (deploy target for Vercel)
```
