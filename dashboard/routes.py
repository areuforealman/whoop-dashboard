import threading
from datetime import date, datetime
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os

from api.calendar import fetch_today_events
from db.database import get_conn, get_sync_state

_sync_status = {"running": False, "message": "Not synced yet"}

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
router = APIRouter()

RECOVERY_DEFAULTS = {"score": None, "hrv_rmssd_milli": None, "resting_heart_rate": None}
SLEEP_DEFAULTS = {"total_sleep_time_milli": None, "sleep_efficiency_percentage": None}
CYCLE_DEFAULTS = {"strain_score": None}


def _query(sql: str, params=()) -> list:
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def _token_exists() -> bool:
    from config import WHOOP_TOKEN_FILE
    return os.path.exists(WHOOP_TOKEN_FILE)


# --- Auth routes ---

@router.get("/auth/start")
async def auth_start():
    from urllib.parse import urlencode
    from config import WHOOP_AUTH_URL, WHOOP_CLIENT_ID, WHOOP_REDIRECT_URI, WHOOP_SCOPES
    import secrets
    state = secrets.token_urlsafe(16)
    params = {
        "client_id": WHOOP_CLIENT_ID,
        "redirect_uri": WHOOP_REDIRECT_URI,
        "response_type": "code",
        "scope": WHOOP_SCOPES,
        "state": state,
    }
    return RedirectResponse(f"{WHOOP_AUTH_URL}?{urlencode(params)}")


@router.get("/auth/callback")
async def auth_callback(code: str, state: str = ""):
    import time, requests as req
    from config import WHOOP_CLIENT_ID, WHOOP_CLIENT_SECRET, WHOOP_REDIRECT_URI, WHOOP_TOKEN_FILE, WHOOP_TOKEN_URL
    import json
    resp = req.post(WHOOP_TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": WHOOP_REDIRECT_URI,
        "client_id": WHOOP_CLIENT_ID,
        "client_secret": WHOOP_CLIENT_SECRET,
    })
    resp.raise_for_status()
    token = resp.json()
    token["expires_at"] = time.time() + token["expires_in"] - 60
    with open(WHOOP_TOKEN_FILE, "w") as f:
        json.dump(token, f)
    # Kick off initial sync in background thread — don't block the redirect
    _start_sync_thread()
    return RedirectResponse("/")


# --- Dashboard ---

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    # Redirect to auth if not connected
    if not _token_exists():
        return RedirectResponse("/auth/start")

    today = date.today().isoformat()

    recovery_rows = _query(
        "SELECT * FROM recoveries WHERE date = ? ORDER BY rowid DESC LIMIT 1", (today,)
    )
    recovery = {**RECOVERY_DEFAULTS, **(recovery_rows[0] if recovery_rows else {})}

    sleep_rows = _query(
        "SELECT * FROM sleeps WHERE date = ? ORDER BY rowid DESC LIMIT 1", (today,)
    )
    if not sleep_rows:
        sleep_rows = _query("SELECT * FROM sleeps ORDER BY date DESC LIMIT 1")
    sleep = {**SLEEP_DEFAULTS, **(sleep_rows[0] if sleep_rows else {})}

    cycle_rows = _query(
        "SELECT * FROM cycles WHERE date = ? ORDER BY rowid DESC LIMIT 1", (today,)
    )
    if not cycle_rows:
        cycle_rows = _query("SELECT * FROM cycles ORDER BY date DESC LIMIT 1")
    cycle = {**CYCLE_DEFAULTS, **(cycle_rows[0] if cycle_rows else {})}

    recoveries_30 = _query(
        "SELECT date, score, hrv_rmssd_milli, resting_heart_rate FROM recoveries ORDER BY date DESC LIMIT 30"
    )
    sleeps_30 = _query(
        "SELECT date, total_sleep_time_milli, sleep_efficiency_percentage FROM sleeps ORDER BY date DESC LIMIT 30"
    )
    strains_30 = _query(
        "SELECT date, strain_score FROM cycles ORDER BY date DESC LIMIT 30"
    )

    mood_logs = _query("SELECT * FROM mood_logs ORDER BY created_at DESC LIMIT 7")
    calendar_events = fetch_today_events()
    last_sync = get_sync_state("last_sync_at")

    return templates.TemplateResponse("index.html", {
        "request": request,
        "today": today,
        "recovery": recovery,
        "sleep": sleep,
        "cycle": cycle,
        "recoveries_30": list(reversed(recoveries_30)),
        "sleeps_30": list(reversed(sleeps_30)),
        "strains_30": list(reversed(strains_30)),
        "mood_logs": mood_logs,
        "calendar_events": calendar_events,
        "last_sync": last_sync,
    })


@router.post("/mood", response_class=JSONResponse)
async def log_mood(energy_level: int = Form(...), note: str = Form("")):
    today = date.today().isoformat()
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO mood_logs (date, energy_level, note, created_at) VALUES (?, ?, ?, ?)",
            (today, energy_level, note.strip(), now),
        )
    return {"status": "ok"}


def _start_sync_thread():
    if _sync_status["running"]:
        return
    def _run():
        from sync.sync import run_sync
        _sync_status["running"] = True
        _sync_status["message"] = "Syncing..."
        try:
            run_sync()
            _sync_status["message"] = "Sync complete"
        except Exception as e:
            _sync_status["message"] = f"Sync error: {e}"
            print(f"Sync error: {e}")
        finally:
            _sync_status["running"] = False
    threading.Thread(target=_run, daemon=True).start()


@router.post("/sync", response_class=JSONResponse)
async def trigger_sync():
    if _sync_status["running"]:
        return {"status": "running", "message": "Sync already in progress"}
    _start_sync_thread()
    return {"status": "started"}


@router.get("/sync/status", response_class=JSONResponse)
async def sync_status():
    return _sync_status
