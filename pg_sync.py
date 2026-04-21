import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()


def fetch_from_pg():
    conn = psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"),
        dbname=os.getenv("PG_DBNAME"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
    )
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT file_uuid_id, create_ts, error, table_name, file_name FROM error_log"
            )
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def sync():
    from db import upsert_from_pg
    records = fetch_from_pg()
    added = upsert_from_pg(records)
    return len(records), added
