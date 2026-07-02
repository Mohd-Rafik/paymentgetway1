"""
Database connection — PostgreSQL (Supabase)
Reads DATABASE_URL from environment and returns a psycopg2 connection.
"""

import os

import psycopg2
from dotenv import load_dotenv

from app.utils.logger import log_info, log_exception

load_dotenv()


class ConnectionWrapper:
    """Thin wrapper that tags the connection with a db_vendor string
    so sp_executor knows which SQL dialect to use."""

    def __init__(self, conn):
        self._conn = conn
        self.db_vendor = "postgres"

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _get_dsn() -> dict:
    """Build psycopg2 DSN from DATABASE_URL env var."""
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not set. "
            "Add it to your .env file: "
            "postgresql://user:password@host:port/dbname"
        )
    return {"dsn": database_url}


def get_connection() -> ConnectionWrapper:
    """
    Open and return a new psycopg2 connection wrapped with ConnectionWrapper.
    Caller is responsible for closing the connection.
    """
    try:
        dsn_kwargs = _get_dsn()
        conn = psycopg2.connect(
            **dsn_kwargs,
            connect_timeout=10,          # fail fast if Supabase unreachable
            options="-c statement_timeout=30000",  # 30s statement timeout
        )
        conn.autocommit = False          # explicit commit/rollback
        return ConnectionWrapper(conn)
    except psycopg2.OperationalError as exc:
        log_exception(f"DB connection failed: {exc}")
        raise RuntimeError(f"Failed to connect to database: {exc}") from exc


def ping_db() -> bool:
    """Quick health check — returns True if DB is reachable."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        log_info("DB ping: OK")
        return True
    except Exception as exc:
        log_exception(f"DB ping failed: {exc}")
        return False
