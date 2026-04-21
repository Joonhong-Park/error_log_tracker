# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트명

**Error Log Tracker** — NiFi CSV→Parquet 변환 실패 오류를 PostgreSQL `error_log`에서 읽어와 원인 파악·조치 내용·조치 여부를 개인적으로 관리하는 Flask 웹 앱.

## 실행 방법

```cmd
pip install -r requirements.txt
python app.py
```

브라우저에서 `http://localhost:5000` 접속.

## 아키텍처

이 앱은 **PostgreSQL(읽기 전용) → SQLite(로컬 관리) → Flask Web UI** 구조로 동작한다.

```
PostgreSQL error_log  (읽기 전용, NiFi가 자동 기록)
        ↓  pg_sync.py  (신규 건만 INSERT, 기존 건 덮어쓰지 않음)
SQLite error_memo.db  (사용자 입력 필드 포함, 앱과 같은 디렉토리에 생성)
        ↓  db.py
Flask app.py          (라우팅)
        ↓
templates/            (index.html 목록, detail.html 상세/수정)
```

### 핵심 설계 원칙

- **PostgreSQL은 절대 수정하지 않는다.** `pg_sync.py`는 SELECT만 수행한다.
- **동기화는 단방향·추가 전용**이다. `upsert_from_pg`는 `file_uuid_id`가 없는 건만 INSERT하며, 이미 존재하는 행의 사용자 입력 필드(`root_cause`, `action_required`, `resolved`)는 건드리지 않는다.
- **조치 완료 건은 기본 목록에서 숨긴다.** `get_list(show_resolved=False)`가 기본값이며, `?show_resolved=1` 쿼리 파라미터로 토글한다. Excel 추출도 동일한 파라미터를 따른다.

### 모듈별 역할

| 파일 | 역할 |
|------|------|
| `pg_sync.py` | PostgreSQL 연결 및 `error_log` 전체 조회, `db.upsert_from_pg` 호출 |
| `db.py` | SQLite CRUD. `DB_PATH`는 스크립트 위치 기준 절대경로로 고정 |
| `app.py` | Flask 라우팅. 앱 시작 시 `db.init_db()` 자동 호출 |

### 데이터 흐름 — 동기화 시

1. `/sync` 라우트 → `pg_sync.sync()` 호출
2. `fetch_from_pg()` — PostgreSQL `error_log` 전체 SELECT
3. `upsert_from_pg(records)` — SQLite에 신규 건만 INSERT, 추가 수 반환
4. 결과를 flash 메시지로 표시 후 `/` 리다이렉트

### SQLite 스키마

```
error_memo (
    file_uuid_id    TEXT PRIMARY KEY,  -- PG에서 복사
    create_ts       TEXT,              -- PG에서 복사
    error           TEXT,              -- PG에서 복사
    table_name      TEXT,              -- PG에서 복사
    file_name       TEXT,              -- PG에서 복사
    root_cause      TEXT,              -- 사용자 입력
    action_required TEXT,              -- 사용자 입력
    resolved        INTEGER DEFAULT 0, -- 사용자 입력 (0/1)
    resolved_at     TEXT               -- resolved=1 저장 시 자동 기록
)
```

## 환경 변수 (.env)

```
PG_HOST, PG_PORT, PG_DBNAME, PG_USER, PG_PASSWORD
```

`pg_sync.py` 최상단에서 `load_dotenv()`로 로드한다.
