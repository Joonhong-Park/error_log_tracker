# Error Log Tracker

NiFi CSV→Parquet 변환 실패 오류를 PostgreSQL `error_log`에서 읽어와  
**원인 파악 · 조치 내용 · 조치 여부**를 개인적으로 관리하는 Flask 웹 앱.

## 시작하기

```bash
pip install -r requirements.txt
python app.py
```

브라우저에서 `http://localhost:5000` 접속 후 **동기화** 버튼 클릭.

## 환경 설정

`.env` 파일을 프로젝트 루트에 생성:

```
PG_HOST=localhost
PG_PORT=5432
PG_DBNAME=your_database
PG_USER=your_user
PG_PASSWORD=your_password
```

## 주요 기능

- PostgreSQL `error_log` 동기화 (읽기 전용, 신규 건만 추가)
- 오류별 원인 파악 / 조치 필요 내용 / 조치 여부 기록
- 조치 완료 건 숨김 (토글로 표시 가능)
- Excel 추출 (현재 필터 기준)
