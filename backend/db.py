"""SQLite locally or PostgreSQL on free hosting; parameterized, atomic writes."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from argon2 import PasswordHasher
import psycopg
from psycopg.rows import dict_row

HASHER = PasswordHasher()


def is_postgres(path):
    return str(path).startswith(("postgresql://", "postgres://"))


class PostgresConnection:
    """Translate only our internal SQL placeholders, never interpolate values."""
    def __init__(self, connection):
        self.connection = connection

    def execute(self, sql, parameters=()):
        return self.connection.execute(sql.replace("?", "%s"), parameters or None)

    def executescript(self, sql):
        self.connection.execute(sql, prepare=False)


@contextmanager
def connect(path: str, *, write: bool = False):
    if is_postgres(path):
        with psycopg.connect(path, row_factory=dict_row, connect_timeout=15) as raw:
            raw.execute("SET LOCAL lock_timeout = '15s'")
            if write:
                # Like BEGIN IMMEDIATE on SQLite: serialize writes in this small app.
                # Transaction-scoped locks also work with Neon pooled connections.
                raw.execute("SELECT pg_advisory_xact_lock(26012026)")
            yield PostgresConnection(raw)
        return
    conn = sqlite3.connect(path, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        if write:
            # Range checks, revocations and writes are atomic, including across workers.
            conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize(path: str, username: str, password: str):
    migrations = Path(__file__).parent / "migrations"
    if is_postgres(path):
        with connect(path, write=True) as conn:
            conn.executescript((migrations / "001_initial.postgres.sql").read_text())
    else:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with connect(path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript((migrations / "001_initial.sql").read_text())
    with connect(path, write=True) as conn:
        if not conn.execute("SELECT 1 FROM admins LIMIT 1").fetchone():
            if not username or len(password) < 12:
                raise RuntimeError("Przy pierwszym uruchomieniu ustaw ADMIN_USERNAME i ADMIN_PASSWORD (min. 12 znaków).")
            conn.execute("INSERT INTO admins(username, password_hash) VALUES (?, ?)",
                         (username, HASHER.hash(password)))
    if not is_postgres(path):
        os.chmod(path, 0o600)


def changed(conn):
    conn.execute("UPDATE changes SET revision = revision + 1 WHERE id = 1")
