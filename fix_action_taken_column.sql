BEGIN TRANSACTION;

ALTER TABLE error_memo RENAME TO _error_memo_backup;

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
);

INSERT INTO error_memo
SELECT message_id, create_date_ts, error, table_name, load_type,
       origin_file_name, root_cause, action_required, action_taken,
       resolved, resolved_date_ts
FROM _error_memo_backup;

DROP TABLE _error_memo_backup;

COMMIT;
