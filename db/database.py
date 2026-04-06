import sqlite3
import os
from typing import Optional
from config import DB_PATH

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with open(SCHEMA_PATH) as f:
        schema = f.read()
    with get_conn() as conn:
        conn.executescript(schema)


def get_sync_state(key: str) -> Optional[str]:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM sync_state WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None


def set_sync_state(key: str, value: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO sync_state (key, value) VALUES (?, ?)",
            (key, value),
        )


def upsert_cycles(records: list[dict]):
    with get_conn() as conn:
        conn.executemany(
            """INSERT OR REPLACE INTO cycles (id, date, strain_score, kilojoules)
               VALUES (:id, :date, :strain_score, :kilojoules)""",
            records,
        )


def upsert_recoveries(records: list[dict]):
    with get_conn() as conn:
        conn.executemany(
            """INSERT OR REPLACE INTO recoveries
               (cycle_id, date, score, hrv_rmssd_milli, resting_heart_rate, sleep_need_baseline_milli)
               VALUES (:cycle_id, :date, :score, :hrv_rmssd_milli, :resting_heart_rate, :sleep_need_baseline_milli)""",
            records,
        )


def upsert_sleeps(records: list[dict]):
    with get_conn() as conn:
        conn.executemany(
            """INSERT OR REPLACE INTO sleeps
               (id, cycle_id, date, total_in_bed_time_milli, total_sleep_time_milli,
                sleep_efficiency_percentage, rem_sleep_time_milli, deep_sleep_time_milli)
               VALUES (:id, :cycle_id, :date, :total_in_bed_time_milli, :total_sleep_time_milli,
                       :sleep_efficiency_percentage, :rem_sleep_time_milli, :deep_sleep_time_milli)""",
            records,
        )


def upsert_workouts(records: list[dict]):
    with get_conn() as conn:
        conn.executemany(
            """INSERT OR REPLACE INTO workouts
               (id, date, sport_id, strain, average_heart_rate, max_heart_rate, duration_milli)
               VALUES (:id, :date, :sport_id, :strain, :average_heart_rate, :max_heart_rate, :duration_milli)""",
            records,
        )
