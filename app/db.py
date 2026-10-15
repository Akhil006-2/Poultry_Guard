import sqlite3
import json
from pathlib import Path
from .config import get_settings

SCHEMA = '''
CREATE TABLE IF NOT EXISTS farms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    location TEXT,
    contact_name TEXT DEFAULT '',
    contact_phone TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS flocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    farm_id INTEGER,
    name TEXT NOT NULL,
    breed TEXT DEFAULT 'Broiler',
    bird_count INTEGER DEFAULT 0,
    age_days INTEGER DEFAULT 0,
    housing_type TEXT DEFAULT 'Deep litter coop',
    status TEXT DEFAULT 'active',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS health_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    farm_id INTEGER,
    flock_id INTEGER,
    event_date TEXT,
    reported_at TEXT DEFAULT CURRENT_TIMESTAMP,
    signs TEXT NOT NULL,
    sick_count INTEGER DEFAULT 0,
    deaths INTEGER DEFAULT 0,
    feed_change TEXT DEFAULT 'unknown',
    water_change TEXT DEFAULT 'unknown',
    notes TEXT DEFAULT '',
    risk_level TEXT DEFAULT 'routine',
    status TEXT DEFAULT 'reported',
    FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE SET NULL,
    FOREIGN KEY(flock_id) REFERENCES flocks(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    farm_id INTEGER,
    flock_id INTEGER,
    original_name TEXT,
    video_path TEXT,
    status TEXT DEFAULT 'queued',
    progress_percent REAL DEFAULT 0.0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    started_at TEXT,
    finished_at TEXT,
    error TEXT,
    metadata_json TEXT,
    result_json TEXT,
    density_config_json TEXT,
    FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE SET NULL,
    FOREIGN KEY(flock_id) REFERENCES flocks(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    frame_index INTEGER,
    timestamp_sec REAL,
    detections INTEGER DEFAULT 0,
    track_ids_json TEXT DEFAULT '[]',
    boxes_json TEXT DEFAULT '[]',
    motion_ratio REAL DEFAULT 0.0,
    density_score REAL DEFAULT 0.0,
    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    farm_id INTEGER,
    flock_id INTEGER,
    job_id TEXT,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    alert_type TEXT DEFAULT 'health_review',
    density_event_id TEXT,
    status TEXT DEFAULT 'open',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TEXT,
    resolved_at TEXT,
    response_time_sec REAL,
    dismiss_reason TEXT DEFAULT '',
    FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE SET NULL,
    FOREIGN KEY(flock_id) REFERENCES flocks(id) ON DELETE SET NULL,
    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS density_events (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    farm_id INTEGER,
    flock_id INTEGER,
    zone_id TEXT NOT NULL,
    grid_layout TEXT NOT NULL,
    frame_index INTEGER NOT NULL,
    timestamp_sec REAL NOT NULL,
    detection_count INTEGER NOT NULL,
    threshold INTEGER NOT NULL,
    occupied_area_pct REAL DEFAULT 0.0,
    start_time_sec REAL,
    end_time_sec REAL,
    duration_sec REAL,
    persistence_frames INTEGER,
    evidence_original_path TEXT,
    evidence_annotated_path TEXT,
    trigger_reason TEXT NOT NULL,
    review_status TEXT DEFAULT 'pending_review',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    notes TEXT DEFAULT '',
    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE SET NULL,
    FOREIGN KEY(flock_id) REFERENCES flocks(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER,
    event_type TEXT NOT NULL,
    recipient TEXT NOT NULL,
    provider TEXT NOT NULL,
    message_text TEXT NOT NULL,
    status TEXT NOT NULL,
    provider_message_id TEXT,
    error_detail TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(alert_id) REFERENCES alerts(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
'''

def connect():
    path = get_settings().database_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA journal_mode=WAL')
    return conn

def _migrate_columns(c):
    # Ensure new tables are created
    c.executescript(SCHEMA)

    # Safely add columns if older database schema exists
    table_cols = {
        'farms': [
            ('contact_name', "TEXT DEFAULT ''"),
            ('contact_phone', "TEXT DEFAULT ''"),
            ('notes', "TEXT DEFAULT ''"),
            ('updated_at', 'TEXT DEFAULT CURRENT_TIMESTAMP'),
        ],
        'flocks': [
            ('housing_type', "TEXT DEFAULT 'Deep litter coop'"),
            ('status', "TEXT DEFAULT 'active'"),
            ('updated_at', 'TEXT DEFAULT CURRENT_TIMESTAMP'),
        ],
        'health_events': [
            ('event_date', 'TEXT'),
        ],
        'jobs': [
            ('farm_id', 'INTEGER'),
            ('flock_id', 'INTEGER'),
            ('progress_percent', 'REAL DEFAULT 0.0'),
            ('density_config_json', 'TEXT'),
        ],
        'alerts': [
            ('alert_type', "TEXT DEFAULT 'health_review'"),
            ('density_event_id', 'TEXT'),
            ('response_time_sec', 'REAL'),
            ('dismiss_reason', "TEXT DEFAULT ''"),
        ],
        'density_events': [
            ('occupied_area_pct', 'REAL DEFAULT 0.0'),
            ('notes', "TEXT DEFAULT ''"),
        ]
    }
    for table, cols in table_cols.items():
        try:
            existing = {r['name'] for r in c.execute(f"PRAGMA table_info({table})").fetchall()}
            for col_name, col_type in cols:
                if col_name not in existing:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
        except Exception:
            pass

def init_db():
    with connect() as c:
        c.executescript(SCHEMA)
        _migrate_columns(c)

def rows(sql, args=()):
    with connect() as c:
        return [dict(r) for r in c.execute(sql, args).fetchall()]

def one(sql, args=()):
    with connect() as c:
        r = c.execute(sql, args).fetchone()
        return dict(r) if r else None

def execute(sql, args=()):
    with connect() as c:
        cur = c.execute(sql, args)
        return cur.lastrowid
