CREATE TABLE IF NOT EXISTS cycles (
    id TEXT PRIMARY KEY,
    date TEXT,
    strain_score REAL,
    kilojoules REAL
);

CREATE TABLE IF NOT EXISTS recoveries (
    cycle_id TEXT PRIMARY KEY,
    date TEXT,
    score INTEGER,
    hrv_rmssd_milli REAL,
    resting_heart_rate INTEGER,
    sleep_need_baseline_milli INTEGER
);

CREATE TABLE IF NOT EXISTS sleeps (
    id TEXT PRIMARY KEY,
    cycle_id TEXT,
    date TEXT,
    total_in_bed_time_milli INTEGER,
    total_sleep_time_milli INTEGER,
    sleep_efficiency_percentage REAL,
    rem_sleep_time_milli INTEGER,
    deep_sleep_time_milli INTEGER
);

CREATE TABLE IF NOT EXISTS workouts (
    id TEXT PRIMARY KEY,
    date TEXT,
    sport_id INTEGER,
    strain REAL,
    average_heart_rate INTEGER,
    max_heart_rate INTEGER,
    duration_milli INTEGER
);

CREATE TABLE IF NOT EXISTS mood_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    energy_level INTEGER,
    note TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS sync_state (
    key TEXT PRIMARY KEY,
    value TEXT
);
