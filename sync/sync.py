from datetime import datetime, timezone

from api.whoop import fetch_cycles, fetch_recoveries, fetch_sleeps, fetch_workouts
from db.database import (
    get_sync_state,
    set_sync_state,
    upsert_cycles,
    upsert_recoveries,
    upsert_sleeps,
    upsert_workouts,
)

LAST_SYNC_KEY = "last_sync_at"


def run_sync():
    """Incrementally fetch new Whoop data since last sync and write to SQLite."""
    last_sync = get_sync_state(LAST_SYNC_KEY)
    print(f"Syncing Whoop data (since: {last_sync or '90 days ago'})...")

    cycles = fetch_cycles(start=last_sync)
    recoveries = fetch_recoveries(start=last_sync)
    sleeps = fetch_sleeps(start=last_sync)
    workouts = fetch_workouts(start=last_sync)

    if cycles:
        upsert_cycles(cycles)
    if recoveries:
        upsert_recoveries(recoveries)
    if sleeps:
        upsert_sleeps(sleeps)
    if workouts:
        upsert_workouts(workouts)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    set_sync_state(LAST_SYNC_KEY, now)

    print(
        f"Sync complete — "
        f"{len(cycles)} cycles, {len(recoveries)} recoveries, "
        f"{len(sleeps)} sleeps, {len(workouts)} workouts"
    )
