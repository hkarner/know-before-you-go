import sqlite3
from pathlib import Path

db_path = Path("data/beaches.db")  # ← your db path
db_path.parent.mkdir(exist_ok=True)
conn = sqlite3.connect(db_path)

conn.executescript("""
CREATE TABLE IF NOT EXISTS beaches (
    id          TEXT PRIMARY KEY,  -- BEACON site ID
    name        TEXT,
    state       TEXT,
    county      TEXT,
    latitude    REAL,
    longitude   REAL,
    water_type  TEXT  -- 'saltwater' | 'freshwater'
);

CREATE TABLE IF NOT EXISTS samples (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    beach_id    TEXT REFERENCES beaches(id),
    sample_date TEXT,  -- ISO-8601
    entero_cfu  REAL,  -- Enterococcus CFU/100mL
    source      TEXT   -- 'BEACON' | 'WQP'
);

CREATE TABLE IF NOT EXISTS grade_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    beach_id    TEXT REFERENCES beaches(id),
    grade_date  TEXT,
    geo_mean    REAL,
    grade       TEXT   -- A/B/C/D/F
);

CREATE TABLE IF NOT EXISTS beach_aliases (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    beach_id    TEXT REFERENCES beaches(id),
    alias       TEXT,   -- colloquial name e.g. 'Rats Beach'
    slug        TEXT,   -- URL-friendly e.g. 'rats-beach'
    surfline_id TEXT,   -- 24-char Surfline spot ID (optional)
    source      TEXT    -- 'manual' | 'osm'
);

CREATE TABLE IF NOT EXISTS alert_subscriptions (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    email                 TEXT,
    beach_id              TEXT REFERENCES beaches(id),
    notify_on_drop        INTEGER DEFAULT 1,
    notify_on_improvement INTEGER DEFAULT 0,
    min_grade_change      INTEGER DEFAULT 1,
    floor_grade           TEXT DEFAULT NULL,
    active                INTEGER DEFAULT 1
);
""")

conn.commit()
conn.close()
print("Database created at data/beaches.db")