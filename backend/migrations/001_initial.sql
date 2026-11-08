PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY);
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    admin_id INTEGER NOT NULL REFERENCES admins(id) ON DELETE CASCADE,
    expires_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires_at);
CREATE TABLE IF NOT EXISTS series (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 100),
    min_value REAL NOT NULL,
    max_value REAL NOT NULL,
    color TEXT NOT NULL,
    icon TEXT,
    unit TEXT CHECK(unit IS NULL OR length(unit) <= 20),
    CHECK(min_value < max_value)
);
CREATE TABLE IF NOT EXISTS sensors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_id INTEGER NOT NULL REFERENCES series(id) ON DELETE CASCADE,
    name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 100),
    key_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    last_measurement_at TEXT
);
CREATE INDEX IF NOT EXISTS sensors_series ON sensors(series_id);
CREATE TABLE IF NOT EXISTS measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_id INTEGER NOT NULL REFERENCES series(id) ON DELETE CASCADE,
    sensor_id INTEGER REFERENCES sensors(id) ON DELETE SET NULL,
    value REAL NOT NULL,
    timestamp TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS measurements_series_time ON measurements(series_id, timestamp);
CREATE INDEX IF NOT EXISTS measurements_time ON measurements(timestamp);
CREATE TABLE IF NOT EXISTS changes (id INTEGER PRIMARY KEY CHECK(id = 1), revision INTEGER NOT NULL);
INSERT OR IGNORE INTO changes VALUES (1, 0);
CREATE TABLE IF NOT EXISTS login_attempts (bucket TEXT NOT NULL, attempted_at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS login_attempts_bucket ON login_attempts(bucket, attempted_at);
INSERT OR IGNORE INTO schema_migrations VALUES (1);
