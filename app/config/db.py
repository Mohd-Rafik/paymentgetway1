import os
import pymssql
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    return pymssql.connect(
        server=os.environ["DB_SERVER"],
        user=os.environ["DB_UID"],
        password=os.environ["DB_PWD"],
        database=os.environ["DB_NAME"],
        tds_version="7.0",
    )