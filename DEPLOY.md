# Deploying GamerLog / L3aderboard

Two services: the **FastAPI backend on Railway** (alongside the managed Postgres)
and the **React frontend on Vercel**. Deploy the backend first so you have a real
API URL to give the frontend.

Config already in the repo:
- `backend/Procfile` — runs `alembic upgrade head` then starts uvicorn on `$PORT`
- `backend/.python-version` — pins Python 3.12 for the build
- `frontend/vercel.json` — SPA fallback so client routes don't 404 on refresh

---

## 1. Backend → Railway

1. In your Railway project (the one with Postgres), **New → GitHub Repo** → select
   `arya-pradhan/L3aderboard`.
2. Open the new service → **Settings**:
   - **Root Directory:** `backend`
   - **Branch:** the branch you deploy from (e.g. `main` after merging)
   - Start command is picked up from the `Procfile`; leave it blank.
3. **Settings → Networking → Generate Domain** (port 8000 isn't needed — Railway
   injects `$PORT`). Note the URL, e.g. `https://l3aderboard-api.up.railway.app`.
4. **Variables** — add:
   | Key | Value |
   |-----|-------|
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (reference the Postgres service — uses the fast internal host) |
   | `JWT_SECRET` | a long random string (`python -c "import secrets;print(secrets.token_urlsafe(48))"`) |
   | `RAWG_API_KEY` | your RAWG key |
   | `CORS_ORIGINS` | your Vercel URL (fill in after step 2) |
   | `FRONTEND_URL` | your Vercel URL (for the Steam redirect) |
   | `STEAM_API_KEY` | optional, only for Steam import |
5. Deploy. Migrations run automatically on boot. Check `‹domain›/health` → `{"status":"ok"}`
   and `‹domain›/docs`.

## 2. Frontend → Vercel

1. [vercel.com/new](https://vercel.com/new) → import `arya-pradhan/L3aderboard`.
2. **Root Directory:** `frontend` (Vercel then auto-detects Vite).
3. **Environment Variables:** `VITE_API_URL` = your Railway backend URL (from 1.3).
4. Deploy. Note the Vercel URL, e.g. `https://l3aderboard.vercel.app`.

## 3. Wire them together

Back in Railway, set (or update) and redeploy:
- `CORS_ORIGINS` = the Vercel URL (exact origin, no trailing slash)
- `FRONTEND_URL` = the Vercel URL

Then open the Vercel URL, register, and confirm the full flow. Done.

> Note: if you add a custom domain on either side, add it to `CORS_ORIGINS`
> (comma-separated) and update `FRONTEND_URL`.
