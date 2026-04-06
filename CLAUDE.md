# CLAUDE.md — Whoop Dashboard

## Project overview
Personal health dashboard built on the Whoop Developer API. Local FastAPI web app + daily Telegram briefing via GitHub Actions. No cloud hosting required for the dashboard.

## Architecture
- **`main.py`** — FastAPI app entry point. Run with `python3 main.py`. Serves on port 8000.
- **`config.py`** — All config loaded from `.env` via `python-dotenv`. Never hardcode credentials.
- **`db/`** — SQLite via stdlib `sqlite3`. Schema in `schema.sql`, helpers in `database.py`. DB file is `whoop.db` (gitignored).
- **`api/whoop.py`** — Whoop OAuth2 client. Token stored in `.whoop_token.json` (gitignored). Auth flow handled by FastAPI routes `/auth/start` and `/auth/callback`.
- **`api/calendar.py`** — Google Calendar API. Credentials in `credentials.json`, token in `.gcal_token.json` (both gitignored). Calendar is optional — fetch failures are caught and return `[]`.
- **`sync/sync.py`** — Incremental sync. Reads `last_sync_at` from `sync_state` table, only fetches records newer than that. Called on dashboard load and by the briefing script.
- **`dashboard/routes.py`** — FastAPI routes: `GET /`, `POST /mood`, `POST /sync`, `GET /auth/start`, `GET /auth/callback`.
- **`dashboard/templates/index.html`** — Single-page Jinja2 template. Uses Chart.js from CDN for charts. No build step.
- **`briefing/send_briefing.py`** — Standalone script. Syncs data, fetches calendar, builds message with rule-based insights, sends via Telegram Bot API.
- **`.github/workflows/daily-briefing.yml`** — GitHub Actions cron (7am UTC). Runs `send_briefing.py` with secrets injected as env vars.

## Key constraints
- **Python 3.9** — use `Optional[X]` from `typing`, not `X | None` syntax (requires 3.10+)
- **No AI layer** — insights are rule-based only (recovery score thresholds)
- **Local-first** — dashboard runs on the user's Mac, not deployed anywhere
- **All free** — Whoop API (free), Telegram (free), GitHub Actions (free tier, ~30 min/month used)

## Environment variables (see `.env.example`)
```
WHOOP_CLIENT_ID        # From developer.whoop.com
WHOOP_CLIENT_SECRET    # From developer.whoop.com
TELEGRAM_BOT_TOKEN     # From @BotFather on Telegram
TELEGRAM_CHAT_ID       # From @userinfobot on Telegram
GCAL_CREDENTIALS       # Optional: contents of credentials.json (used in GitHub Actions)
PORT                   # Optional: defaults to 8000
```

## GitHub Actions secrets needed
`WHOOP_CLIENT_ID`, `WHOOP_CLIENT_SECRET`, `WHOOP_REFRESH_TOKEN`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `GCAL_CREDENTIALS` (optional)

`WHOOP_REFRESH_TOKEN` is found in `.whoop_token.json` after first local login.

## Common tasks

**Start dashboard locally:**
```bash
python3 main.py
# then open http://localhost:8000
```

**Run briefing manually:**
```bash
python3 briefing/send_briefing.py
```

**Re-sync data:**
Click "↻ Sync now" on the dashboard, or `POST /sync`.

## What NOT to do
- Do not store credentials in code or commit `.env`, `*.json` token files, or `whoop.db`
- Do not add AI/LLM calls without discussing first — currently intentionally rule-based
- Do not change the OAuth redirect URI without updating it on developer.whoop.com too
- Do not use `str | None` syntax — must stay Python 3.9 compatible
