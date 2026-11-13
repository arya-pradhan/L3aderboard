# Deploying GamerLog / L3aderboard

Three pieces: **Postgres on Neon**, the **FastAPI backend on Render**, and the
**React frontend on Vercel**. Set up the database first, then the backend, so
you have a real API URL to give the frontend.

Config already in the repo:
- `backend/.python-version` pins Python 3.12 for the build.
- `frontend/vercel.json` adds an SPA fallback so client routes don't 404 on refresh.

---

## 1. Database → Neon

1. [console.neon.tech](https://console.neon.tech) → New Project.
2. Link the repo and pull the connection strings (already done once with
   `neon init` + `neon deploy`; `neon.ts` and the `.neon` link live at the repo root):
   ```bash
   neon env pull   # writes DATABASE_URL + DATABASE_URL_UNPOOLED to .env.local (gitignored)
   ```
   - `DATABASE_URL` is the **pooled** (`-pooler`) URL for app traffic. The app
     turns off asyncpg's statement cache for PgBouncer automatically.
   - `DATABASE_URL_UNPOOLED` is the **direct** URL. Alembic uses it for migrations.
   Paste both as-is. The app rewrites the SSL params for asyncpg.
3. Schema: migrations run on every Render boot (`alembic upgrade head` over the
   direct URL). The `production` branch is already at head.
4. Bot users for the feed (needs `RAWG_API_KEY`; set `BOT_PASSWORD` or the script
   prints a generated one). Run once from the Render service's **Shell** tab:
   ```bash
   python -m scripts.seed_bots
   ```

Note: Neon's free tier suspends the database when idle. The first query after a
pause takes about a second longer, and `pool_pre_ping` handles the reconnect.

## 2. Backend → Render

1. [dashboard.render.com](https://dashboard.render.com) → **New → Web Service** →
   connect `arya-pradhan/L3aderboard`.
2. Settings:
   - **Root Directory:** `backend`
   - **Runtime:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance type:** Free
3. **Environment** — add:
   | Key | Value |
   |-----|-------|
   | `DATABASE_URL` | Neon pooled URL (`DATABASE_URL` from `.env.local`) |
   | `DATABASE_URL_UNPOOLED` | Neon direct URL (`DATABASE_URL_UNPOOLED` from `.env.local`), used for migrations |
   | `JWT_SECRET` | a long random string (`python -c "import secrets;print(secrets.token_urlsafe(48))"`) |
   | `RAWG_API_KEY` | your RAWG key |
   | `DEEPSEEK_API_KEY` | your DeepSeek key (powers the Assistant page) |
   | `CORS_ORIGINS` | your Vercel URL |
   | `FRONTEND_URL` | your Vercel URL (for the Steam redirect) |
   | `STEAM_API_KEY` | optional, only needed for Steam import |
4. Deploy. Migrations run on every boot. Check `‹render-url›/health` → `{"status":"ok"}`.

Note: the free tier sleeps after ~15 minutes idle, so the first request after
that takes about 30–50s to wake it up.

## 3. Frontend → Vercel

1. [vercel.com/new](https://vercel.com/new) → import `arya-pradhan/L3aderboard`
   (or open the existing project).
2. **Root Directory:** `frontend` (Vercel then auto-detects Vite).
3. **Environment Variables:** set `VITE_API_URL` to the Render URL from step 2,
   then **redeploy** (Vite bakes it in at build time).

## 4. Wire up

- On Render, set `CORS_ORIGINS` and `FRONTEND_URL` to the exact Vercel origin
  (no trailing slash).
- Open the Vercel URL, log in, and check the library, feed, and **Assistant** pages.
- Railway is retired. Its data wasn't migrated (the service was offline), so
  existing users need to re-register.

> If you add a custom domain on either side, add it to `CORS_ORIGINS`
> (comma-separated) and update `FRONTEND_URL`.
