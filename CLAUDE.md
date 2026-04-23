# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트명

**Error Log Tracker** — NiFi CSV→Parquet 변환 실패 오류를 PostgreSQL `error_log`에서 읽어와 원인 파악·조치 내용·조치 여부를 개인적으로 관리하는 Flask 웹 앱.

## 실행 방법

```cmd
pip install -r requirements.txt
python app.py
```

브라우저가 자동으로 `http://localhost:5000`에 열린다.

## exe 빌드

```cmd
pip install pyinstaller
pyinstaller --onefile --noconsole --add-data "templates;templates" --name ErrorLogTracker app.py
```

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
- **동기화는 단방향·추가 전용**이다. `upsert_from_pg`는 `INSERT OR IGNORE`로 신규 건만 INSERT하며, 이미 존재하는 행의 사용자 입력 필드(`root_cause`, `action_required`, `resolved`)는 건드리지 않는다.
- **조치 완료 건은 기본 목록에서 숨긴다.** `get_list(show_resolved=False)`가 기본값이며, `?show_resolved=1` 쿼리 파라미터로 토글한다. Excel 추출도 동일한 파라미터를 따른다.
- **PG 접속 정보는 `pg_sync.py` 상단 상수로 고정한다.** `.env` 및 별도 설정 파일을 사용하지 않는다.
- **exe 단독 배포가 가능하다.** PyInstaller로 빌드 시 `sys.frozen` 분기로 templates/DB 경로를 보정한다.
- **서버는 `127.0.0.1`에만 바인딩한다.** 개인용 로컬 앱이므로 외부 네트워크에 노출하지 않는다.

### 모듈별 역할

| 파일 | 역할 |
|------|------|
| `pg_sync.py` | 상단 상수로 PG 접속 정보 관리. `error_log` 전체 SELECT 후 `upsert_from_pg` 호출. PG timestamp → `YYYY-MM-DD HH:MM:SS` 변환 |
| `db.py` | SQLite CRUD. `DB_PATH`는 실행 환경(개발/exe)에 따라 자동 결정. `upsert_from_pg`는 `INSERT OR IGNORE` + `executemany`로 N+1 없이 일괄 처리. `get_filter_options()`로 타입 드롭다운용 distinct 값 제공 |
| `app.py` | Flask 라우팅. 앱 시작 시 `db.init_db()` 자동 호출. exe 빌드 시 template_folder 경로 보정. 1초 딜레이 후 브라우저 자동 오픈 (서버 준비 대기) |

### 데이터 흐름 — 동기화 시

1. `/sync` 라우트 → `pg_sync.sync()` 호출
2. `fetch_from_pg()` — 상수로 PG 접속 후 `error_log` 전체 SELECT
3. `upsert_from_pg(records)` — SQLite에 신규 건만 INSERT, 추가 수 반환
4. 결과를 flash 메시지로 표시 후 `/` 리다이렉트

### 목록 화면 기능

- **페이지네이션**: 50건/페이지, `«` `‹` 숫자 `›` `»` 버튼
- **필터**: 기간(date_from/date_to), 테이블명(텍스트 정확히 일치), 타입(드롭다운 distinct), 오류 내용(LIKE 검색)
- **정렬**: 발생시각·파일명·테이블명·타입·조치여부 헤더 클릭 시 ASC/DESC 토글
- **Excel 추출**: 현재 필터+정렬 상태 그대로 전체 추출

### SQLite 스키마

```
error_memo (
    message_id       TEXT PRIMARY KEY,  -- PG에서 복사
    create_date_ts   TEXT,              -- PG에서 복사 (YYYY-MM-DD HH:MM:SS)
    error            TEXT,              -- PG에서 복사
    table_name       TEXT,              -- PG에서 복사
    table_type       TEXT,              -- PG에서 복사
    origin_file_name TEXT,              -- PG에서 복사
    root_cause       TEXT,              -- 사용자 입력
    action_required  TEXT,              -- 사용자 입력
    resolved         INTEGER DEFAULT 0, -- 사용자 입력 (0/1)
    resolved_date_ts TEXT               -- resolved=1 저장 시 자동 기록 (YYYY-MM-DD HH:MM:SS)
)
```

### DB 경로 결정 로직

```python
# exe 실행 시 → exe 파일 옆
if getattr(sys, "frozen", False):
    DB_PATH = os.path.join(os.path.dirname(sys.executable), "error_memo.db")
# 개발 시 → 소스 파일 옆
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error_memo.db")
```
