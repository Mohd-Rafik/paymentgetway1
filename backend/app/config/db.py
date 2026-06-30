import os
import pyodbc
from dotenv import load_dotenv
 
load_dotenv()
 
 
def get_connection():
    trusted = os.environ.get("DB_TRUSTED_CONNECTION", "no").lower() == "yes"

    if trusted:
        conn_str = (
            f"DRIVER={os.environ['DB_DRIVER']};"
            f"SERVER={os.environ['DB_SERVER']};"
            f"DATABASE={os.environ['DB_NAME']};"
            f"Trusted_Connection=yes;"
        )
    else:
        conn_str = (
            f"DRIVER={os.environ['DB_DRIVER']};"
            f"SERVER={os.environ['DB_SERVER']};"
            f"DATABASE={os.environ['DB_NAME']};"
            f"UID={os.environ['DB_UID']};"
            f"PWD={os.environ['DB_PWD']};"
        )
    return pyodbc.connect(conn_str)