import sqlite3
import os
import sys

if getattr(sys, "frozen", False):
    DB_PATH = os.path.join(os.path.dirname(sys.executable), "error_memo.db")
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error_memo.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS error_memo (
                file_uuid_id    TEXT PRIMARY KEY,
                create_ts       TEXT,
                error           TEXT,
                table_name      TEXT,
                file_name       TEXT,
                root_cause      TEXT,
                action_required TEXT,
                resolved        INTEGER DEFAULT 0,
                resolved_at     TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key   TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()


def get_config():
    with get_conn() as conn:
        rows = conn.execute("SELECT key, value FROM config").fetchall()
    return {r["key"]: r["value"] for r in rows}


def set_config(data: dict):
    with get_conn() as conn:
        for key, value in data.items():
            conn.execute(
                "INSERT INTO config(key, value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )
        conn.commit()


def upsert_from_pg(records):
    """PG에서 가져온 레코드를 SQLite에 추가 (신규 건만, 사용자 입력 필드 유지)."""
    with get_conn() as conn:
        added = 0
        for r in records:
            exists = conn.execute(
                "SELECT 1 FROM error_memo WHERE file_uuid_id = ?", (r["file_uuid_id"],)
            ).fetchone()
            if not exists:
                conn.execute(
                    """INSERT INTO error_memo
                       (file_uuid_id, create_ts, error, table_name, file_name)
                       VALUES (?, ?, ?, ?, ?)""",
                    (r["file_uuid_id"], r["create_ts"], r["error"], r["table_name"], r["file_name"]),
                )
                added += 1
        conn.commit()
    return added


def get_list(show_resolved: bool = False):
    sql = "SELECT * FROM error_memo"
    if not show_resolved:
        sql += " WHERE resolved = 0"
    sql += " ORDER BY create_ts DESC"
    with get_conn() as conn:
        return conn.execute(sql).fetchall()


def get_one(file_uuid_id: str):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM error_memo WHERE file_uuid_id = ?", (file_uuid_id,)
        ).fetchone()


def update_memo(file_uuid_id: str, root_cause: str, action_required: str, resolved: bool):
    from datetime import datetime
    resolved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if resolved else None

    with get_conn() as conn:
        conn.execute(
            """UPDATE error_memo
               SET root_cause = ?, action_required = ?, resolved = ?, resolved_at = ?
               WHERE file_uuid_id = ?""",
            (root_cause, action_required, int(resolved), resolved_at, file_uuid_id),
        )
        conn.commit()
