from datetime import date, datetime
from decimal import Decimal

import pymssql

from app.utils.logger import log_info, log_exception


def make_json_safe(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def execute_stored_procedure(conn, procedure_name: str, params: tuple = (), fetch: bool = False, commit: bool = True):
    cursor = None

    try:
        params = params or ()
        cursor = conn.cursor()

        if params:
            placeholders = ", ".join(["%s"] * len(params))
            query = f"EXEC {procedure_name} {placeholders}"
        else:
            query = f"EXEC {procedure_name}"

        log_info(f"Executing SP: {procedure_name} with params={params}")
        cursor.execute(query, params)

        data = []
        if fetch and cursor.description:
            columns = [col[0] for col in cursor.description]
            for row in cursor.fetchall():
                data.append({col: make_json_safe(val) for col, val in zip(columns, row)})

        if commit:
            conn.commit()

        return {"success": True, "message": "Stored procedure executed successfully", "data": data, "error": None}

    except pymssql.Error as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        log_exception(f"Database error in {procedure_name}: {str(e)}")
        return {"success": False, "message": "Database error", "data": None, "error": str(e)}

    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        log_exception(f"Internal error in {procedure_name}: {str(e)}")
        return {"success": False, "message": "Internal server error", "data": None, "error": str(e)}

    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass