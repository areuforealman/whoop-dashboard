import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import requests

from config import (
    WHOOP_API_BASE,
    WHOOP_CLIENT_ID,
    WHOOP_CLIENT_SECRET,
    WHOOP_TOKEN_FILE,
    WHOOP_TOKEN_URL,
)


def _load_token() -> Optional[dict]:
    if os.path.exists(WHOOP_TOKEN_FILE):
        with open(WHOOP_TOKEN_FILE) as f:
            return json.load(f)
    return None


def _save_token(token: dict):
    with open(WHOOP_TOKEN_FILE, "w") as f:
        json.dump(token, f)


def _refresh_token(token: dict) -> dict:
    resp = requests.post(
        WHOOP_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": token["refresh_token"],
            "client_id": WHOOP_CLIENT_ID,
            "client_secret": WHOOP_CLIENT_SECRET,
        },
    )
    resp.raise_for_status()
    new_token = resp.json()
    new_token["expires_at"] = time.time() + new_token["expires_in"] - 60
    _save_token(new_token)
    return new_token


def _get_token() -> dict:
    """Load token from file, refresh if expired, or run OAuth flow if missing."""
    token = _load_token()

    # GitHub Actions: bootstrap from env var refresh token
    if token is None and os.getenv("WHOOP_REFRESH_TOKEN"):
        token = {
            "refresh_token": os.environ["WHOOP_REFRESH_TOKEN"],
            "expires_at": 0,
        }

    if token:
        if time.time() >= token.get("expires_at", 0):
            token = _refresh_token(token)
        return token

    raise RuntimeError("No Whoop token found. Visit http://localhost:8000 to authenticate.")


def _headers() -> dict:
    token = _get_token()
    return {"Authorization": f"Bearer {token['access_token']}"}


def _paginate(path: str, params: Optional[dict] = None) -> list:
    """Fetch all pages from a Whoop paginated endpoint with retry on 429."""
    results = []
    url = f"{WHOOP_API_BASE}{path}"
    p = dict(params or {})
    p["limit"] = 25
    while url:
        for attempt in range(5):
            resp = requests.get(url, headers=_headers(), params=p)
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 2 ** (attempt + 1)))
                print(f"Rate limited — waiting {wait}s before retry...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            break
        data = resp.json()
        results.extend(data.get("records", []))
        next_token = data.get("next_token")
        if next_token:
            p = {"next_token": next_token, "limit": 25}
        else:
            url = None
        time.sleep(0.5)  # small delay between pages to avoid rate limits
    return results


def _date_param(days_ago: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# --- Public fetch functions ---

def fetch_cycles(start: Optional[str] = None) -> list[dict]:
    params = {"start": start or _date_param(90)}
    raw = _paginate("/cycle", params)
    results = []
    for r in raw:
        score = r.get("score") or {}
        results.append({
            "id": str(r["id"]),
            "date": r["start"][:10],
            "strain_score": score.get("strain"),
            "kilojoules": score.get("kilojoule"),
        })
    return results


def fetch_recoveries(start: Optional[str] = None) -> list[dict]:
    params = {"start": start or _date_param(90)}
    raw = _paginate("/recovery", params)
    results = []
    for r in raw:
        score = r.get("score") or {}
        sleep_need = (r.get("sleep_need") or {}).get("baseline_milli")
        results.append({
            "cycle_id": str(r["cycle_id"]),
            "date": r.get("updated_at", "")[:10],
            "score": score.get("recovery_score"),
            "hrv_rmssd_milli": score.get("hrv_rmssd_milli"),
            "resting_heart_rate": score.get("resting_heart_rate"),
            "sleep_need_baseline_milli": sleep_need,
        })
    return results


def fetch_sleeps(start: Optional[str] = None) -> list[dict]:
    params = {"start": start or _date_param(90)}
    raw = _paginate("/activity/sleep", params)
    results = []
    for r in raw:
        score = r.get("score") or {}
        stages = score.get("stage_summary") or {}
        results.append({
            "id": str(r["id"]),
            "cycle_id": str(r.get("cycle_id", "")),
            "date": r["start"][:10],
            "total_in_bed_time_milli": score.get("total_in_bed_time_milli"),
            "total_sleep_time_milli": score.get("total_sleep_time_milli"),
            "sleep_efficiency_percentage": score.get("sleep_efficiency_percentage"),
            "rem_sleep_time_milli": stages.get("total_rem_sleep_time_milli"),
            "deep_sleep_time_milli": stages.get("total_slow_wave_sleep_time_milli"),
        })
    return results


def fetch_workouts(start: Optional[str] = None) -> list[dict]:
    params = {"start": start or _date_param(90)}
    raw = _paginate("/activity/workout", params)
    results = []
    for r in raw:
        score = r.get("score") or {}
        results.append({
            "id": str(r["id"]),
            "date": r["start"][:10],
            "sport_id": r.get("sport_id"),
            "strain": score.get("strain"),
            "average_heart_rate": score.get("average_heart_rate"),
            "max_heart_rate": score.get("max_heart_rate"),
            "duration_milli": (
                int((datetime.fromisoformat(r["end"].replace("Z", "+00:00")) -
                     datetime.fromisoformat(r["start"].replace("Z", "+00:00"))).total_seconds() * 1000)
                if r.get("end") else None
            ),
        })
    return results
