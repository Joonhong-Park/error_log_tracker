# Error Log Tracker

NiFi CSV→Parquet 변환 실패 오류를 PostgreSQL `error_log`에서 읽어와  
**원인 파악 · 조치 내용 · 조치 여부**를 개인적으로 관리하는 Flask 웹 앱.

## 시작하기

```bash
pip install -r requirements.txt
python app.py
```

브라우저가 자동으로 `http://localhost:5000`에 열립니다.  
최초 실행 시 **[DB 설정]** 버튼을 눌러 PostgreSQL 접속 정보를 입력하세요.

## DB 접속 설정

`.env` 파일 없이 앱 내 설정 화면에서 직접 입력합니다.

1. 목록 화면 우측 상단 **[DB 설정]** 클릭
2. HOST / PORT / DATABASE / USER / PASSWORD 입력 후 저장
3. **[동기화]** 버튼으로 PG 데이터 가져오기

설정값은 `error_memo.db` 안의 `config` 테이블에 저장되며, 다음 실행부터는 재입력 불필요.

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
- Excel 추출 (현재 필터 기준)
- PG 접속 설정 UI (앱 내 저장, .env 불필요)
