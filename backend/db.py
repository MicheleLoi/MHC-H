# Part of MHC-H. AGPL v3 — see LICENSE-AGPL
"""
db.py — MHC-H SQLite storage for signup + auth + governance pipeline.

Single source of truth for the keystore + applications + governance schema.

Original schema (api_keys, applications, stripe_events_processed) is embedded
verbatim from the MHC-L Phase 1 cross-product canon (signup_auth_architecture.md
§4). The three governance tables (lawyer_sessions, decisions, artifacts) are
added here for the MHC-H MVP.

Storage path:
  Resolved from env var MHC_API_DB_PATH, defaulting to ~/.mhc-h-keystore.db.

Concurrency:
  WAL mode enabled at init time. Concurrent readers (auth middleware on every
  HTTP request) + occasional writers (Stripe webhook, signup, REST endpoints).
  WAL is the right default; cost is one extra `-wal` and `-shm` file alongside
  the DB.

Stdlib only.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DB_PATH_ENV = "MHC_API_DB_PATH"
DEFAULT_DB_PATH = Path.home() / ".mhc-h-keystore.db"

# Original auth/signup tables — unchanged from MHC-L canon §4.
# Plus three new governance tables (lawyer_sessions, decisions, artifacts)
# specified in the MHC-H MVP plan (la-scelta-b-woolly-pizza.md Fase 1).
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS applications (
  id                           TEXT PRIMARY KEY,
  email                        TEXT NOT NULL,
  firm                         TEXT,
  role                         TEXT,
  use_case                     TEXT,
  notes                        TEXT,
  submitted_at                 TIMESTAMP NOT NULL,
  status                       TEXT CHECK (status IN ('pending','approved','rejected','withdrawn')),
  reviewed_at                  TIMESTAMP,
  reviewed_by                  TEXT,
  rejection_reason             TEXT,
  stripe_checkout_session_id   TEXT
);

CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_applications_email  ON applications(email);

CREATE TABLE IF NOT EXISTS api_keys (
  key_hash                 TEXT PRIMARY KEY,
  user_email               TEXT NOT NULL,
  application_id           TEXT NOT NULL REFERENCES applications(id),
  stripe_customer_id       TEXT NOT NULL,
  stripe_subscription_id   TEXT NOT NULL,
  tier                     TEXT,
  status                   TEXT CHECK (status IN ('active','revoked','expired','past_due')),
  created_at               TIMESTAMP NOT NULL,
  revoked_at               TIMESTAMP,
  revoked_reason           TEXT,
  last_used_at             TIMESTAMP,
  request_count            INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_api_keys_customer ON api_keys(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_email    ON api_keys(user_email);
CREATE INDEX IF NOT EXISTS idx_api_keys_status   ON api_keys(status);

CREATE TABLE IF NOT EXISTS stripe_events_processed (
  event_id        TEXT PRIMARY KEY,
  event_type      TEXT NOT NULL,
  processed_at    TIMESTAMP NOT NULL
);

-- ---------------------------------------------------------------------------
-- Governance tables (MHC-H MVP — Fase 1)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS lawyer_sessions (
  sid          TEXT PRIMARY KEY,
  user_email   TEXT NOT NULL,
  project_name TEXT,
  state_json   TEXT NOT NULL,
  started_at   TIMESTAMP NOT NULL,
  ended_at     TIMESTAMP,
  exported     INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_lawyer_sessions_email ON lawyer_sessions(user_email);

CREATE TABLE IF NOT EXISTS decisions (
  decision_id   TEXT PRIMARY KEY,
  user_email    TEXT NOT NULL,
  sid           TEXT,
  topic         TEXT NOT NULL,
  context       TEXT,
  options_json  TEXT,
  decision      TEXT NOT NULL,
  rationale     TEXT,
  created_at    TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_decisions_email ON decisions(user_email);

CREATE TABLE IF NOT EXISTS artifacts (
  artifact_id   TEXT PRIMARY KEY,
  user_email    TEXT NOT NULL,
  sid           TEXT,
  artifact_type TEXT NOT NULL,
  title         TEXT,
  content_md    TEXT NOT NULL,
  created_at    TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_artifacts_email ON artifacts(user_email);
"""


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def resolve_db_path() -> Path:
    """Return the SQLite DB path: env override or DEFAULT_DB_PATH."""
    env_path = os.environ.get(DB_PATH_ENV)
    if env_path:
        return Path(env_path).expanduser()
    return DEFAULT_DB_PATH


# ---------------------------------------------------------------------------
# Connection + init
# ---------------------------------------------------------------------------

def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """
    Open a SQLite connection with sane defaults for the signup + governance
    pipelines.

    - row_factory = sqlite3.Row → dict-like access by column name
    - foreign_keys = ON         → enforces api_keys.application_id REFERENCES
    - WAL journal mode          → concurrent readers + writers
    - synchronous = NORMAL      → durable enough for MVP; pairs well with WAL

    The connection is the caller's responsibility to close. Prefer the
    `connection()` context manager below for short-lived operations.
    """
    path = db_path or resolve_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), isolation_level=None)  # autocommit; we manage tx explicitly
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def init_db(db_path: Path | None = None) -> Path:
    """
    Create tables + indexes if they don't exist. Idempotent.

    Returns the resolved path so callers can log it.
    """
    path = db_path or resolve_db_path()
    conn = connect(path)
    try:
        conn.executescript(SCHEMA_SQL)
    finally:
        conn.close()
    return path


@contextmanager
def connection(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Context manager: open + always close a SQLite connection."""
    conn = connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


__all__ = [
    "DB_PATH_ENV",
    "DEFAULT_DB_PATH",
    "SCHEMA_SQL",
    "resolve_db_path",
    "connect",
    "init_db",
    "connection",
]
