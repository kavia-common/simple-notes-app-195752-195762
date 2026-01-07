"""SQLite database utilities for the notes backend.

This module reads the database file path from the database container's
`db_connection.txt` file (as required by the task instructions) and provides
a small connection helper suitable for FastAPI request handling.
"""

from __future__ import annotations

import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator


def _repo_root_from_this_file() -> Path:
    """Compute monorepo root path from this file location.

    notes_backend/src/api/db.py -> notes_backend -> workspace root
    """
    return Path(__file__).resolve().parents[3]


def _parse_db_path_from_connection_file(text: str) -> str | None:
    """Parse an absolute file path from db_connection.txt contents."""
    # Expected line example:
    # "# File path: /home/.../simple-notes-app-.../database/myapp.db"
    m = re.search(r"^\s*#\s*File path:\s*(.+?)\s*$", text, flags=re.MULTILINE)
    if m:
        return m.group(1).strip()
    return None


# PUBLIC_INTERFACE
def get_db_path() -> str:
    """Return the SQLite database file path.

    The path is sourced from the database container's `db_connection.txt`.
    If the file cannot be read or parsed, we fall back to the SQLITE_DB
    environment variable if present.

    Raises:
        RuntimeError: If neither db_connection.txt nor SQLITE_DB yields a path.
    """
    repo_root = _repo_root_from_this_file()
    connection_file = repo_root / "database" / "db_connection.txt"

    if connection_file.exists():
        try:
            text = connection_file.read_text(encoding="utf-8")
            parsed = _parse_db_path_from_connection_file(text)
            if parsed:
                return parsed
        except Exception:
            # If parsing fails, try env fallback below.
            pass

    env_path = os.getenv("SQLITE_DB")
    if env_path:
        return env_path

    raise RuntimeError(
        "SQLite database path not found. Ensure database/db_connection.txt exists "
        "and contains a '# File path: ...' line, or set SQLITE_DB env var."
    )


def _connect_sqlite(db_path: str) -> sqlite3.Connection:
    """Create a SQLite connection with safe defaults for API usage."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Safe default; doesn't hurt if no FK constraints.
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def sqlite_connection() -> Generator[sqlite3.Connection, None, None]:
    """Context manager yielding a SQLite connection.

    Ensures connection is closed. Does not auto-commit; callers should commit
    when they perform writes.
    """
    conn = _connect_sqlite(get_db_path())
    try:
        yield conn
    finally:
        conn.close()


# PUBLIC_INTERFACE
def utc_now_iso() -> str:
    """Return current UTC time as ISO-8601 string without microseconds."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
