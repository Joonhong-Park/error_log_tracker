# Error Log Tracker

NiFi CSV→Parquet 변환 실패 오류를 PostgreSQL `error_log`에서 읽어와  
**원인 파악 · 조치 내용 · 조치 여부**를 개인적으로 관리하는 Flask 웹 앱.

## 시작하기

```bash
pip install -r requirements.txt
python app.py
```

브라우저가 자동으로 `http://localhost:5000`에 열립니다.

## PG 접속 정보 설정

`pg_sync.py` 상단 상수를 직접 수정합니다.

```python
PG_HOST     = "your_host"
PG_PORT     = "5432"
PG_DBNAME   = "your_dbname"
PG_USER     = "your_user"
PG_PASSWORD = "your_password"
```

## exe 빌드 (Windows)

```cmd
pip install pyinstaller
pyinstaller --onefile --noconsole --add-data "templates;templates" --name ErrorLogTracker app.py
```

`dist\ErrorLogTracker.exe` 단일 파일로 배포 가능. 별도 설치 불필요.

```
배포폴더/
└── ErrorLogTracker.exe   ← 이것만 전달
    (error_memo.db 는 첫 실행 시 자동 생성)
```

## 주요 기능

- PostgreSQL `error_log` 동기화 (읽기 전용, 신규 건만 추가)
- 오류별 원인 파악 / 조치 필요 내용 / 조치 여부 기록
- 조치 완료 건 숨김 (토글로 표시 가능)
- 기간 / 테이블명 / 타입 / 오류 내용 키워드 필터
- 컬럼 헤더 클릭 정렬 (오름차순/내림차순)
- 페이지네이션 (50건/페이지)
- Excel 추출 (현재 필터 기준 전체)

## SQLite 직접 수정

앱 UI 외에 DB 파일을 직접 조작할 수 있습니다.

### 방법 1 — DB Browser for SQLite (GUI, 추천)

1. [sqlitebrowser.org](https://sqlitebrowser.org) 설치
2. `error_memo.db` 열기 → **Browse Data** 탭 → `error_memo` 테이블
3. 셀 클릭 후 직접 수정 → **Write Changes** 저장

### 방법 2 — Python 스크립트

```python
import sqlite3

conn = sqlite3.connect("error_memo.db")

# 단건 업데이트
conn.execute("""
    UPDATE error_memo
    SET root_cause = '원인 내용', action_required = '조치 내용', resolved = 0
    WHERE file_uuid_id = '대상-uuid'
""")

# 조치 완료 일괄 처리
conn.execute("""
    UPDATE error_memo
    SET resolved = 1, resolved_time_ts = datetime('now', 'localtime')
    WHERE table_name = '테이블명' AND resolved = 0
""")

conn.commit()
conn.close()
```

### 방법 3 — SQLite CLI

```cmd
sqlite3 error_memo.db

UPDATE error_memo
SET root_cause = '원인', resolved = 1, resolved_time_ts = datetime('now', 'localtime')
WHERE file_uuid_id = '대상-uuid';

.quit
```

### 컬럼 참고

| 컬럼 | 설명 | 수정 가능 |
|------|------|----------|
| `file_uuid_id` | PK (PG에서 복사) | X |
| `create_time_ts` | 오류 발생 시각 | X |
| `error` | 오류 내용 | X |
| `table_name` | 테이블명 | X |
| `table_type` | 테이블 유형 | X |
| `file_name` | 파일명 | X |
| `root_cause` | 원인 파악 | O |
| `action_required` | 조치 필요 내용 | O |
| `resolved` | 조치 여부 (0/1) | O |
| `resolved_time_ts` | 완료 처리 일시 | O |
