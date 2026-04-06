"""
Daily Telegram briefing script.
Run locally: python briefing/send_briefing.py
Run via GitHub Actions: triggered by cron
"""
import os
import sys

# Allow running from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import date, datetime, timezone

import requests
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

from api.calendar import fetch_today_events
from db.database import get_conn, init_db
from sync.sync import run_sync


def _query_one(sql: str, params=()) -> dict:
    with get_conn() as conn:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else {}


def _recovery_insight(recovery_score: Optional[int], yesterday_strain: Optional[float]) -> str:
    if recovery_score is None:
        return "No recovery data yet — check Whoop app."
    if yesterday_strain and yesterday_strain > 18 and recovery_score < 50:
        return "High strain yesterday — prioritise rest and sleep tonight."
    if recovery_score >= 67:
        return "Good recovery — solid day for a hard session."
    if recovery_score >= 34:
        return "Moderate recovery — keep effort controlled today."
    return "Low recovery — rest or light activity only."


def _format_sleep(total_ms: Optional[int], efficiency: Optional[float]) -> str:
    if not total_ms:
        return "—"
    h = int(total_ms / 3600000)
    m = int((total_ms % 3600000) / 60000)
    eff = f" / {efficiency:.0f}% eff" if efficiency else ""
    return f"{h}h {m}m{eff}"


def _format_events(events: list[dict]) -> str:
    if not events:
        return "Clear"
    lines = []
    for e in events[:5]:
        start = e.get("start", "")
        time_str = start[11:16] if "T" in start else "All day"
        lines.append(f"  {time_str}  {e['title']}")
    if len(events) > 5:
        lines.append(f"  + {len(events) - 5} more")
    return "\n".join(lines)


def build_message() -> str:
    today = date.today()
    day_str = today.strftime("%A %-d %b").upper()

    recovery = _query_one(
        "SELECT score, hrv_rmssd_milli, resting_heart_rate FROM recoveries ORDER BY date DESC LIMIT 1"
    )
    sleep = _query_one(
        "SELECT total_sleep_time_milli, sleep_efficiency_percentage FROM sleeps ORDER BY date DESC LIMIT 1"
    )
    yesterday_cycle = _query_one(
        "SELECT strain_score FROM cycles ORDER BY date DESC LIMIT 1"
    )

    recovery_score = recovery.get("score")
    hrv = recovery.get("hrv_rmssd_milli")
    rhr = recovery.get("resting_heart_rate")
    strain_yesterday = yesterday_cycle.get("strain_score")

    # Recovery colour emoji
    if recovery_score is None:
        rec_emoji = "⚪"
    elif recovery_score >= 67:
        rec_emoji = "🟢"
    elif recovery_score >= 34:
        rec_emoji = "🟡"
    else:
        rec_emoji = "🔴"

    insight = _recovery_insight(recovery_score, strain_yesterday)
    events = fetch_today_events()
    calendar_str = _format_events(events)
    busy = len(events) >= 4

    lines = [
        f"📅 {day_str}",
        "",
        f"Recovery:  {rec_emoji} {recovery_score}%" if recovery_score is not None else "Recovery:  —",
        f"HRV:       {hrv:.0f} ms" if hrv else "HRV:       —",
        f"Resting HR: {rhr} bpm" if rhr else "Resting HR: —",
        f"Sleep:     {_format_sleep(sleep.get('total_sleep_time_milli'), sleep.get('sleep_efficiency_percentage'))}",
        f"Strain:    {strain_yesterday:.1f} yesterday" if strain_yesterday else "Strain:    —",
        "",
        f"📆 {'Busy day ahead' if busy else 'Calendar'}:",
        calendar_str,
        "",
        f"💡 {insight}",
    ]
    return "\n".join(lines)


def send_telegram(message: str):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": message, "parse_mode": ""},
        timeout=10,
    )
    resp.raise_for_status()
    print("Telegram message sent.")


if __name__ == "__main__":
    init_db()
    print("Running sync...")
    run_sync()
    print("Building message...")
    msg = build_message()
    print("\n--- Preview ---")
    print(msg)
    print("--- End ---\n")
    send_telegram(msg)
