import sqlite3
import os
import sys
from datetime import datetime

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
                load_type        TEXT,
                origin_file_name TEXT,
                root_cause       TEXT,
                action_required  TEXT,
                action_taken     TEXT,
                resolved         INTEGER DEFAULT 0,
                resolved_date_ts TEXT
            )
        """)
        col_order = [r[1] for r in conn.execute("PRAGMA table_info(error_memo)").fetchall()]
        # action_taken 없으면 ADD COLUMN (맨 뒤에 붙음)
        if "action_taken" not in col_order:
            conn.execute("ALTER TABLE error_memo ADD COLUMN action_taken TEXT")
            col_order = [r[1] for r in conn.execute("PRAGMA table_info(error_memo)").fetchall()]
        # action_taken이 resolved보다 뒤에 있으면 테이블 재생성으로 순서 교정
        if col_order.index("action_taken") > col_order.index("resolved"):
            conn.execute("ALTER TABLE error_memo RENAME TO _error_memo_old")
            conn.execute("""
                CREATE TABLE error_memo (
                    message_id       TEXT PRIMARY KEY,
                    create_date_ts   TEXT,
                    error            TEXT,
                    table_name       TEXT,
                    load_type        TEXT,
                    origin_file_name TEXT,
                    root_cause       TEXT,
                    action_required  TEXT,
                    action_taken     TEXT,
                    resolved         INTEGER DEFAULT 0,
                    resolved_date_ts TEXT
                )
            """)
            conn.execute("""
                INSERT INTO error_memo
                SELECT message_id, create_date_ts, error, table_name, load_type,
                       origin_file_name, root_cause, action_required, action_taken,
                       resolved, resolved_date_ts
                FROM _error_memo_old
            """)
            conn.execute("DROP TABLE _error_memo_old")
        conn.commit()


_SORT_COLUMNS = {"create_date_ts", "origin_file_name", "table_name", "load_type", "resolved"}


def get_list(show_resolved: bool = False, date_from: str = None, date_to: str = None,
             table_name: str = None, load_type: str = None, error_search: str = None,
             cause_search: str = None,
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
    if load_type:
        conditions.append("load_type = ?")
        params.append(load_type)
    if error_search:
        conditions.append("error LIKE ?")
        params.append(f"%{error_search}%")
    if cause_search:
        conditions.append("root_cause LIKE ?")
        params.append(f"%{cause_search}%")

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
        load_types = [r[0] for r in conn.execute(
            "SELECT DISTINCT load_type FROM error_memo WHERE load_type IS NOT NULL ORDER BY load_type"
        ).fetchall()]
    return load_types


def upsert_from_pg(records):
    with get_conn() as conn:
        cur = conn.executemany(
            """INSERT OR IGNORE INTO error_memo
               (message_id, create_date_ts, error, table_name, load_type, origin_file_name)
               VALUES (:message_id, :create_date_ts, :error, :table_name, :load_type, :origin_file_name)""",
            records,
        )
        conn.commit()
    return cur.rowcount


def get_one(message_id: str):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM error_memo WHERE message_id = ?", (message_id,)
        ).fetchone()


def update_memo(message_id: str, root_cause: str, action_required: str, action_taken: str, resolved: bool):
    resolved_date_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if resolved else None

    with get_conn() as conn:
        conn.execute(
            """UPDATE error_memo
               SET root_cause = ?, action_required = ?, action_taken = ?, resolved = ?, resolved_date_ts = ?
               WHERE message_id = ?""",
            (root_cause, action_required, action_taken, int(resolved), resolved_date_ts, message_id),
        )
        conn.commit()
