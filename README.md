# Whoop Dashboard

A personal health intelligence system built on top of your Whoop data. Local web dashboard + daily Telegram briefing, entirely free to run.

## What it does

- **Dashboard** — single-page view of today's recovery, HRV, sleep, and strain with 30-day trend charts
- **Calendar context** — shows today's Google Calendar events alongside your health metrics
- **Mood log** — quick daily energy/notes check-in stored locally
- **Daily Telegram briefing** — automated morning summary with rule-based insights, sent via GitHub Actions

## Stack

- Python 3.9+, FastAPI, SQLite, Chart.js
- Whoop Developer API (OAuth2)
- Google Calendar API (OAuth2, optional)
- Telegram Bot API
- GitHub Actions (free cron scheduler)

## Project structure

```
whoop-dashboard/
├── main.py                        # Entry point — run this to start the dashboard
├── config.py                      # Config and env loading
├── requirements.txt
├── .env.example                   # Copy to .env and fill in credentials
├── db/
│   ├── schema.sql                 # SQLite schema
│   └── database.py                # DB helpers and upsert functions
├── api/
│   ├── whoop.py                   # Whoop OAuth2 client + data fetchers
│   └── calendar.py                # Google Calendar client
├── sync/
│   └── sync.py                    # Incremental sync engine
├── dashboard/
│   ├── routes.py                  # FastAPI routes
│   └── templates/index.html       # Single-page dashboard UI
├── briefing/
│   └── send_briefing.py           # Telegram briefing script
└── .github/workflows/
    └── daily-briefing.yml         # GitHub Actions cron (7am UTC daily)
```

## Setup

### 1. Install dependencies
```bash
pip3 install -r requirements.txt
```

### 2. Configure credentials
```bash
cp .env.example .env
```
Fill in `WHOOP_CLIENT_ID` and `WHOOP_CLIENT_SECRET` from [developer.whoop.com](https://developer.whoop.com).

When creating your Whoop app, use these settings:
- Redirect URL: `http://localhost:8000/auth/callback`
- Scopes: `read:recovery`, `read:cycles`, `read:sleep`, `read:workout`

### 3. Start the dashboard
```bash
python3 main.py
```
Open [http://localhost:8000](http://localhost:8000) — you'll be redirected to Whoop to authenticate. Once approved, a 90-day backfill runs automatically.

### 4. Set up Telegram briefing
1. Message **@BotFather** on Telegram → `/newbot` → copy the token
2. Message **@userinfobot** → copy your chat ID
3. Add both to `.env`:
   ```
   TELEGRAM_BOT_TOKEN=your_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```
4. Test locally:
   ```bash
   python3 briefing/send_briefing.py
   ```

### 5. Set up Google Calendar (optional)
1. Enable the Google Calendar API in [Google Cloud Console](https://console.cloud.google.com)
2. Create OAuth credentials → download as `credentials.json` → place in project root
3. On first run the dashboard will open a browser to authenticate

### 6. Set up GitHub Actions (daily briefing)
Add these as secrets in your GitHub repo settings → Secrets:
- `WHOOP_CLIENT_ID`
- `WHOOP_CLIENT_SECRET`
- `WHOOP_REFRESH_TOKEN` — copy `refresh_token` value from `.whoop_token.json` after first login
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `GCAL_CREDENTIALS` — contents of `credentials.json` as a single line (optional)

The cron runs at 7am UTC. Adjust the schedule in `.github/workflows/daily-briefing.yml` to match your timezone.

## Running the briefing manually
```bash
python3 briefing/send_briefing.py
```

## Notes
- All data is stored locally in `whoop.db` (SQLite)
- Credentials are never committed — `.env`, token files, and `whoop.db` are all in `.gitignore`
- The sync button on the dashboard fetches any new data since the last sync
