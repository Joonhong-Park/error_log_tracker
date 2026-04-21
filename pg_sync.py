import psycopg2
import psycopg2.extras


def fetch_from_pg():
    from db import get_config
    cfg = get_config()

    required = ["PG_HOST", "PG_PORT", "PG_DBNAME", "PG_USER", "PG_PASSWORD"]
    missing = [k for k in required if not cfg.get(k)]
    if missing:
        raise RuntimeError(f"DB 접속 설정이 없습니다. 설정 화면에서 입력해 주세요. (미설정: {', '.join(missing)})")

    conn = psycopg2.connect(
        host=cfg["PG_HOST"],
        port=cfg["PG_PORT"],
        dbname=cfg["PG_DBNAME"],
        user=cfg["PG_USER"],
        password=cfg["PG_PASSWORD"],
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
