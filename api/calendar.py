import json
import os
from datetime import datetime, timezone

from config import GCAL_CREDENTIALS_FILE, GCAL_SCOPES, GCAL_TOKEN_FILE


def _get_service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None

    # GitHub Actions: load credentials from env var
    gcal_env = os.getenv("GCAL_CREDENTIALS")
    if gcal_env and not os.path.exists(GCAL_CREDENTIALS_FILE):
        with open(GCAL_CREDENTIALS_FILE, "w") as f:
            f.write(gcal_env)

    if os.path.exists(GCAL_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(GCAL_TOKEN_FILE, GCAL_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(GCAL_CREDENTIALS_FILE, GCAL_SCOPES)
            creds = flow.run_local_server(port=0)
        with open(GCAL_TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def fetch_today_events() -> list[dict]:
    """Fetch today's Google Calendar events. Returns list of {title, start, end}."""
    try:
        service = _get_service()
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()

        result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=start_of_day,
                timeMax=end_of_day,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = []
        for item in result.get("items", []):
            start = item["start"].get("dateTime", item["start"].get("date", ""))
            end = item["end"].get("dateTime", item["end"].get("date", ""))
            events.append({
                "title": item.get("summary", "Untitled"),
                "start": start,
                "end": end,
            })
        return events
    except Exception as e:
        print(f"Calendar fetch failed: {e}")
        return []
