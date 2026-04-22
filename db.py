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
                message_id       TEXT PRIMARY KEY,
                create_date_ts   TEXT,
                error            TEXT,
                table_name       TEXT,
                table_type       TEXT,
                origin_file_name TEXT,
                root_cause       TEXT,
                action_required  TEXT,
                resolved         INTEGER DEFAULT 0,
                resolved_date_ts TEXT
            )
        """)
        conn.commit()


_SORT_COLUMNS = {"create_date_ts", "origin_file_name", "table_name", "table_type", "resolved"}


def get_list(show_resolved: bool = False, date_from: str = None, date_to: str = None,
             table_name: str = None, table_type: str = None, error_search: str = None,
             sort_by: str = "create_date_ts", sort_dir: str = "desc",
             page: int = 1, per_page: int = 50):
    if sort_by not in _SORT_COLUMNS:
        sort_by = "create_date_ts"
    sort_dir = "ASC" if sort_dir.lower() == "asc" else "DESC"

    conditions, params = [], []
    if not show_resolved:
        conditions.append("resolved = 0")
    if date_from:
        conditions.append("create_date_ts >= ?")
        params.append(date_from + " 00:00:00")
    if date_to:
        conditions.append("create_date_ts <= ?")
        params.append(date_to + " 23:59:59")
    if table_name:
        conditions.append("table_name = ?")
        params.append(table_name)
    if table_type:
        conditions.append("table_type = ?")
        params.append(table_type)
    if error_search:
        conditions.append("error LIKE ?")
        params.append(f"%{error_search}%")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    order = f"ORDER BY {sort_by} {sort_dir}"

    with get_conn() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM error_memo {where}", params).fetchone()[0]
        if per_page is None:
            rows = conn.execute(
                f"SELECT * FROM error_memo {where} {order}", params
            ).fetchall()
        else:
            offset = (page - 1) * per_page
            rows = conn.execute(
                f"SELECT * FROM error_memo {where} {order} LIMIT ? OFFSET ?",
                params + [per_page, offset],
            ).fetchall()
    return rows, total


def get_filter_options():
    with get_conn() as conn:
        table_types = [r[0] for r in conn.execute(
            "SELECT DISTINCT table_type FROM error_memo WHERE table_type IS NOT NULL ORDER BY table_type"
        ).fetchall()]
    return table_types


def upsert_from_pg(records):
    with get_conn() as conn:
        added = 0
        for r in records:
            exists = conn.execute(
                "SELECT 1 FROM error_memo WHERE message_id = ?", (r["message_id"],)
            ).fetchone()
            if not exists:
                conn.execute(
                    """INSERT INTO error_memo
                       (message_id, create_date_ts, error, table_name, table_type, origin_file_name)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (r["message_id"], r["create_date_ts"], r["error"], r["table_name"], r["table_type"], r["origin_file_name"]),
                )
                added += 1
        conn.commit()
    return added


def get_one(message_id: str):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM error_memo WHERE message_id = ?", (message_id,)
        ).fetchone()


def update_memo(message_id: str, root_cause: str, action_required: str, resolved: bool):
    from datetime import datetime
    resolved_date_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if resolved else None

    with get_conn() as conn:
        conn.execute(
            """UPDATE error_memo
               SET root_cause = ?, action_required = ?, resolved = ?, resolved_date_ts = ?
               WHERE message_id = ?""",
            (root_cause, action_required, int(resolved), resolved_date_ts, message_id),
        )
        conn.commit()
