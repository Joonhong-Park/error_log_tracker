import psycopg2
import psycopg2.extras

PG_HOST     = "your_host"
PG_PORT     = "5432"
PG_DBNAME   = "your_dbname"
PG_USER     = "your_user"
PG_PASSWORD = "your_password"


def fetch_from_pg():
    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DBNAME,
        user=PG_USER,
        password=PG_PASSWORD,
    )
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT message_id, create_date_ts, error, table_name, table_type, origin_file_name FROM error_log"
            )
            rows = cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if d["create_date_ts"] is not None:
                d["create_date_ts"] = str(d["create_date_ts"])[:19]  # YYYY-MM-DD HH:MM:SS
            result.append(d)
        return result
    finally:
        conn.close()


def sync():
    from db import upsert_from_pg
    records = fetch_from_pg()
    added = upsert_from_pg(records)
    return len(records), added
