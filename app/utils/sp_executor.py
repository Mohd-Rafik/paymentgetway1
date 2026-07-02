"""
Stored procedure executor — PostgreSQL (psycopg2) only.
Handles JSONB params, datetime serialization, commit/rollback, and error logging.
"""

import json
from datetime import date, datetime
from decimal import Decimal

import psycopg2

from app.utils.logger import log_info, log_exception


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

def _json_safe(value):
    """Convert DB types that are not JSON-serializable."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _prepare_param(value):
    """
    Convert Python dict/list → JSON string so psycopg2 passes it
    correctly as JSONB to PostgreSQL functions.
    """
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return value


# --------------------------------------------------------------------------- #
# Core executor                                                                #
# --------------------------------------------------------------------------- #

def execute_stored_procedure(
    conn,
    procedure_name: str,
    params: tuple = (),
    fetch: bool = False,
    commit: bool = True,
) -> dict:
    """
    Call a PostgreSQL function via SELECT public.<name>(<placeholders>).

    Returns:
        {"success": True,  "data": [...], "error": None}
        {"success": False, "data": None,  "error": "<message>"}
    """
    cursor = None

    try:
        params = tuple(_prepare_param(p) for p in (params or ()))
        proc = procedure_name if "." in procedure_name else f"public.{procedure_name}"

        if params:
            placeholders = ", ".join(["%s"] * len(params))
            query = f"SELECT {proc}({placeholders})"
        else:
            query = f"SELECT {proc}()"

        log_info(f"Executing SP: {proc}  params_count={len(params)}")

        cursor = conn.cursor()
        cursor.execute(query, params)

        data = []
        if fetch and cursor.description:
            columns = [col[0] for col in cursor.description]
            for row in cursor.fetchall():
                data.append({col: _json_safe(val) for col, val in zip(columns, row)})

        if commit:
            conn.commit()

        return {"success": True, "message": "OK", "data": data, "error": None}

    except psycopg2.Error as exc:
        _safe_rollback(conn)
        msg = str(exc).strip()
        log_exception(f"DB error in {procedure_name}: {msg}")
        return {"success": False, "message": "Database error", "data": None, "error": msg}

    except Exception as exc:
        _safe_rollback(conn)
        msg = str(exc).strip()
        log_exception(f"Unexpected error in {procedure_name}: {msg}")
        return {"success": False, "message": "Internal server error", "data": None, "error": msg}

    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass


def _safe_rollback(conn):
    try:
        conn.rollback()
    except Exception:
        pass