# 작업 계획서

## 1. 작업 개요

| 항목 | 내용 |
|---|---|
| 작업명 | A 테이블 컬럼 추가 및 인덱스 생성 |
| 대상 DB | PostgreSQL |
| 대상 테이블 | A |
| 작업 도구 | DBeaver |
| 작업 유형 | DDL (컬럼 추가, 인덱스 생성) |
| 예상 소요 시간 | 5분 이내 |
| 작업 가능 시간대 | INSERT/UPDATE 중단 가능한 시간대 |

---

## 2. 작업 배경

A 테이블은 현재 에러 로그 기록 용도로 운영 중이며, 재시도 상태 추적 및 원인 분석을 위한 컬럼이 부재한 상태입니다.
이를 보완하기 위해 컬럼 추가 및 조회 성능 확보를 위한 인덱스를 생성합니다.

---

## 3. 변경 내용

### 3-1. 컬럼 추가

| 컬럼명 | 타입 | NULL | 설명 |
|---|---|---|---|
| `retry_status` | VARCHAR | 허용 | 재시도 결과 (SUCCESS / FAILED) |
| `uuid` | VARCHAR | 허용 | 연관 추적용 식별자 |
| `update_date` | TIMESTAMP | 허용 | 마지막 업데이트 시각 |
| `error_reason` | TEXT | 허용 | 원인 분석 내용 |

### 3-2. 인덱스 생성

| 인덱스명 | 대상 컬럼 | 타입 |
|---|---|---|
| `a_update_date_idx` | `update_date` | B-tree |

---

## 4. 사전 준비

### 4-1. Auto Commit OFF 확인
- DBeaver 하단 상태바 `Auto` 버튼 비활성화 확인
- 또는 상단 메뉴 `Connection` → `Auto-commit` 체크 해제

### 4-2. 백업 수행
- DBeaver 상단 메뉴 `Database` → `Backup`
- 대상 테이블 A 선택
- Format: `Custom` 선택 후 실행

### 4-3. 현재 테이블 구조 스냅샷 저장

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'a'
ORDER BY ordinal_position;
```

---

## 5. 작업 순서

### Step 1. 트랜잭션 시작

```sql
BEGIN;
```

### Step 2. 컬럼 추가

```sql
ALTER TABLE A
    ADD COLUMN retry_status  VARCHAR,
    ADD COLUMN uuid          VARCHAR,
    ADD COLUMN update_date   TIMESTAMP,
    ADD COLUMN error_reason  TEXT;
```

### Step 3. 변경 내용 확인

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'a'
ORDER BY ordinal_position;
```

### Step 4. 커밋

```sql
COMMIT;
```

> ⚠️ Step 3 확인 후 이상 없을 때만 COMMIT. 문제 발생 시 ROLLBACK 수행

### Step 5. 인덱스 생성

COMMIT 완료 후 **새 SQL 탭**에서 실행

```sql
CREATE INDEX a_update_date_idx ON A (update_date);
```

> ⚠️ CREATE INDEX는 트랜잭션 외부에서 수행. Step 4 COMMIT 완료 후 별도 실행

### Step 6. 최종 검증

```sql
-- 컬럼 확인
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'a'
ORDER BY ordinal_position;

-- 인덱스 확인
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'a';
```

---

## 6. 롤백 계획

| 상황 | 조치 |
|---|---|
| Step 4 COMMIT 이전 이상 감지 | SQL 편집기에서 ROLLBACK 수행 |
| COMMIT 이후 이상 감지 | DBeaver Restore로 백업본 복구 |

### 트랜잭션 롤백

```sql
ROLLBACK;
```

### 백업 복구 절차
- DBeaver 상단 메뉴 `Database` → `Restore`
- 백업 파일 선택 후 대상 테이블 A 지정하여 복구

---

## 7. 작업 후 확인 항목

- [ ] Auto Commit OFF 상태로 작업 수행 여부 확인
- [ ] 추가된 컬럼 4개 정상 확인
- [ ] 기존 데이터 정합성 이상 없음 (기존 row의 신규 컬럼값 NULL 정상)
- [ ] 인덱스 생성 정상 확인
- [ ] INSERT/UPDATE 재개 후 정상 동작 확인
