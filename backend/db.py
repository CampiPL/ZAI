"""SQLite: parameterized queries and serialized write transactions."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from argon2 import PasswordHasher

HASHER = PasswordHasher()


@contextmanager
def connect(path: str, *, write: bool = False):
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
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript((Path(__file__).parent / "migrations/001_initial.sql").read_text())
    with connect(path, write=True) as conn:
        if not conn.execute("SELECT 1 FROM admins LIMIT 1").fetchone():
            if not username or len(password) < 12:
                raise RuntimeError("Przy pierwszym uruchomieniu ustaw ADMIN_USERNAME i ADMIN_PASSWORD (min. 12 znaków).")
            conn.execute("INSERT INTO admins(username, password_hash) VALUES (?, ?)",
                         (username, HASHER.hash(password)))
    os.chmod(path, 0o600)


def changed(conn):
    conn.execute("UPDATE changes SET revision = revision + 1 WHERE id = 1")
