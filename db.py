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
                create_time_ts  TEXT,
                error           TEXT,
                table_name      TEXT,
                table_type      TEXT,
                file_name       TEXT,
                root_cause      TEXT,
                action_required TEXT,
                resolved        INTEGER DEFAULT 0,
                resolved_time_ts TEXT
            )
        """)
        # 구버전 컬럼명 마이그레이션
        cols = {r[1] for r in conn.execute("PRAGMA table_info(error_memo)")}
        if "create_ts" in cols:
            conn.execute("ALTER TABLE error_memo RENAME COLUMN create_ts TO create_time_ts")
        if "resolved_at" in cols:
            conn.execute("ALTER TABLE error_memo RENAME COLUMN resolved_at TO resolved_time_ts")
        if "table_type" not in cols:
            conn.execute("ALTER TABLE error_memo ADD COLUMN table_type TEXT")
        conn.commit()


def upsert_from_pg(records):
    with get_conn() as conn:
        added = 0
        for r in records:
            exists = conn.execute(
                "SELECT 1 FROM error_memo WHERE file_uuid_id = ?", (r["file_uuid_id"],)
            ).fetchone()
            if not exists:
                conn.execute(
                    """INSERT INTO error_memo
                       (file_uuid_id, create_time_ts, error, table_name, table_type, file_name)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (r["file_uuid_id"], r["create_ts"], r["error"], r["table_name"], r["table_type"], r["file_name"]),
                )
                added += 1
        conn.commit()
    return added


def get_list(show_resolved: bool = False, date_from: str = None, date_to: str = None,
             page: int = 1, per_page: int = 50):
    conditions, params = [], []
    if not show_resolved:
        conditions.append("resolved = 0")
    if date_from:
        conditions.append("create_time_ts >= ?")
        params.append(date_from + " 00:00:00")
    if date_to:
        conditions.append("create_time_ts <= ?")
        params.append(date_to + " 23:59:59")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    with get_conn() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM error_memo {where}", params).fetchone()[0]
        if per_page is None:
            rows = conn.execute(
                f"SELECT * FROM error_memo {where} ORDER BY create_time_ts DESC", params
            ).fetchall()
        else:
            offset = (page - 1) * per_page
            rows = conn.execute(
                f"SELECT * FROM error_memo {where} ORDER BY create_time_ts DESC LIMIT ? OFFSET ?",
                params + [per_page, offset],
            ).fetchall()
    return rows, total


def get_one(file_uuid_id: str):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM error_memo WHERE file_uuid_id = ?", (file_uuid_id,)
        ).fetchone()


def update_memo(file_uuid_id: str, root_cause: str, action_required: str, resolved: bool):
    from datetime import datetime
    resolved_time_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if resolved else None

    with get_conn() as conn:
        conn.execute(
            """UPDATE error_memo
               SET root_cause = ?, action_required = ?, resolved = ?, resolved_time_ts = ?
               WHERE file_uuid_id = ?""",
            (root_cause, action_required, int(resolved), resolved_time_ts, file_uuid_id),
        )
        conn.commit()
