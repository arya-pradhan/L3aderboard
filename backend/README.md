# GamerLog — Backend (FastAPI)

FastAPI + SQLModel (async) + PostgreSQL backend for GamerLog.

## Layout

```
app/
  main.py            FastAPI app, CORS, /health, router include
  core/              config, db session, security (JWT/password), deps
  models/            SQLModel tables: User, Game, LibraryEntry, Follow
  schemas/           Pydantic request/response models
  api/routes/        route modules (auth, ... more per step)
  services/          RAWG / Steam / recommender (added in later steps)
alembic/             async migrations
tests/               pytest (runs on in-memory SQLite; no Postgres needed)
```

## Local setup

```bash
cd backend
python -m venv .venv
# Windows (Git Bash):
source .venv/Scripts/activate
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then edit .env (DATABASE_URL, JWT_SECRET)
```

Generate a JWT secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Database migrations (Alembic, async)

With `DATABASE_URL` set in `.env` (Railway Postgres):

```bash
alembic revision --autogenerate -m "initial schema"   # first time only
alembic upgrade head
```

## Run the API

```bash
uvicorn app.main:app --reload
```

- Health check: http://127.0.0.1:8000/health
- Interactive docs: http://127.0.0.1:8000/docs

## Tests

```bash
pytest
```

Tests use an in-memory SQLite database, so they require neither Postgres nor a
migration — handy for CI and fast local feedback.
