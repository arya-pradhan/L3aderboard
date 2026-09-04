repo: arya-pradhan/L3aderboard
branch: main
path: backend

## Last sync

date: 2026-09-04T15:52:00Z

### Updated in this project

- Read the FastAPI backend (models, schemas, library/games routes, RAWG + Steam services) — repo has no frontend yet.
- Built first UI mockups from the real data model: statuses playing/completed/dropped/backlog, 1–10 ratings, hours_played, manual vs steam_import source.
- Home (editorial carousels), own profile (stats, top 4, library), game detail with reviews and Twitch live channels.
- Collections and Top 4 are new concepts — no backend tables exist for them yet.

## Screen map

| Project screen | Repo files it was built from |
| --- | --- |
| Home / discover (1a, 1b) | backend/app/api/routes/games.py, backend/app/services/rawg.py, backend/app/models/game.py |
| Profile (1c, 1d) | backend/app/models/user.py, backend/app/models/library.py, backend/app/models/follow.py, backend/app/api/routes/library.py |
| Game detail (1e) | backend/app/schemas/game.py, backend/app/services/rawg.py, backend/app/api/routes/library.py |
| Game card treatments (1f) | backend/app/schemas/game.py (GameRead, LibraryEntryRead) |
