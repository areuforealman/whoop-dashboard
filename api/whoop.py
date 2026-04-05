import json
import os
import secrets
import time
import webbrowser
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from config import (
    WHOOP_API_BASE,
    WHOOP_AUTH_URL,
    WHOOP_CLIENT_ID,
    WHOOP_CLIENT_SECRET,
    WHOOP_REDIRECT_URI,
    WHOOP_SCOPES,
    WHOOP_TOKEN_FILE,
    WHOOP_TOKEN_URL,
)

_auth_code = None


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code
        params = parse_qs(urlparse(self.path).query)
        _auth_code = params.get("code", [None])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"<h2>Authenticated! You can close this tab.</h2>")

    def log_message(self, *args):
        pass


def _load_token() -> dict | None:
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

    # Interactive OAuth flow (local only)
    global _auth_code
    _auth_code = None
    state = secrets.token_urlsafe(16)

    auth_params = {
        "client_id": WHOOP_CLIENT_ID,
        "redirect_uri": WHOOP_REDIRECT_URI,
        "response_type": "code",
        "scope": WHOOP_SCOPES,
        "state": state,
    }
    auth_url = f"{WHOOP_AUTH_URL}?{urlencode(auth_params)}"
    print(f"\nOpening browser for Whoop authentication...\n{auth_url}\n")
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", 8000), _CallbackHandler)
    while _auth_code is None:
        server.handle_request()
    server.server_close()

    resp = requests.post(
        WHOOP_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": _auth_code,
            "redirect_uri": WHOOP_REDIRECT_URI,
            "client_id": WHOOP_CLIENT_ID,
            "client_secret": WHOOP_CLIENT_SECRET,
        },
    )
    resp.raise_for_status()
    token = resp.json()
    token["expires_at"] = time.time() + token["expires_in"] - 60
    _save_token(token)
    return token


def _headers() -> dict:
    token = _get_token()
    return {"Authorization": f"Bearer {token['access_token']}"}


def _paginate(path: str, params: dict | None = None) -> list:
    """Fetch all pages from a Whoop paginated endpoint."""
    results = []
    url = f"{WHOOP_API_BASE}{path}"
    p = dict(params or {})
    p["limit"] = 25
    while url:
        resp = requests.get(url, headers=_headers(), params=p)
        resp.raise_for_status()
        data = resp.json()
        results.extend(data.get("records", []))
        next_token = data.get("next_token")
        if next_token:
            p = {"next_token": next_token, "limit": 25}
        else:
            url = None
    return results


def _date_param(days_ago: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# --- Public fetch functions ---

def fetch_cycles(start: str | None = None) -> list[dict]:
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


def fetch_recoveries(start: str | None = None) -> list[dict]:
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


def fetch_sleeps(start: str | None = None) -> list[dict]:
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


def fetch_workouts(start: str | None = None) -> list[dict]:
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
