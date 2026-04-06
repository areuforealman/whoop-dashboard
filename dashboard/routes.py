from datetime import date, datetime
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import os

from api.calendar import fetch_today_events
from db.database import get_conn, get_sync_state

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
router = APIRouter()


def _query(sql: str, params=()) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    # Today's metrics
    today = date.today().isoformat()

    recovery = _query(
        "SELECT * FROM recoveries WHERE date = ? ORDER BY rowid DESC LIMIT 1", (today,)
    )
    recovery = recovery[0] if recovery else {}

    sleep = _query(
        "SELECT * FROM sleeps WHERE date = ? ORDER BY rowid DESC LIMIT 1", (today,)
    )
    # Fall back to yesterday's sleep (sleep records often land the next day)
    if not sleep:
        sleep = _query("SELECT * FROM sleeps ORDER BY date DESC LIMIT 1")
    sleep = sleep[0] if sleep else {}

    cycle = _query(
        "SELECT * FROM cycles WHERE date = ? ORDER BY rowid DESC LIMIT 1", (today,)
    )
    if not cycle:
        cycle = _query("SELECT * FROM cycles ORDER BY date DESC LIMIT 1")
    cycle = cycle[0] if cycle else {}

    # 30-day trend data for charts
    recoveries_30 = _query(
        "SELECT date, score, hrv_rmssd_milli, resting_heart_rate FROM recoveries ORDER BY date DESC LIMIT 30"
    )
    sleeps_30 = _query(
        "SELECT date, total_sleep_time_milli, sleep_efficiency_percentage FROM sleeps ORDER BY date DESC LIMIT 30"
    )
    strains_30 = _query(
        "SELECT date, strain_score FROM cycles ORDER BY date DESC LIMIT 30"
    )

    # Mood logs (last 7)
    mood_logs = _query(
        "SELECT * FROM mood_logs ORDER BY created_at DESC LIMIT 7"
    )

    # Calendar events
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


@router.post("/sync", response_class=JSONResponse)
async def trigger_sync():
    from sync.sync import run_sync
    try:
        run_sync()
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
