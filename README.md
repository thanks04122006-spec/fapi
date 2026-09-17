# 용산꿈나무도서관 AI 혼잡도 안내 API

DB 없이 CSV(pandas) 기반으로 동작하는 FastAPI 백엔드입니다. 원본 방문자수 엑셀을 업로드하면
표준 세로형으로 전처리해 `data/processed/standard_long.csv`에 누적 저장하고,
이 데이터로 통계/혼잡도 API를 제공합니다.

## 요구 사항

- Python 3.10 이상 (`str | None` 같은 최신 타입 힌트 문법을 사용합니다)

## 설치 및 실행

```bash
git clone <이 저장소 URL>
cd <저장소 폴더명>

python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

uvicorn app.main:app --reload
```

> **반드시 `app` 폴더가 보이는 위치(프로젝트 루트)에서 실행하세요.**
> `main.py`가 아니라 `app.main:app`으로 지정해야 합니다.

실행 후 `http://localhost:8000/docs`에서 Swagger UI로 바로 테스트할 수 있습니다.

다른 기기(휴대폰 등)나 별도 프론트 서버에서 접근해야 하면:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 프로젝트 구조

```
app/
  core/
    config.py     # 게이트명 매핑, 혼잡도 분위수 기준, 경로 등 전역 설정
    errors.py     # 공통 오류 응답 규격 (DATA_NOT_FOUND / INVALID_DATE / EXCEL_FORMAT_ERROR / PROCESSING_ERROR)
  models/
    schemas.py    # 전처리/집계/API 응답에 대응하는 Pydantic 스키마
  services/
    preprocessing.py  # 가로형 원본 -> 표준 세로형 변환
    data_store.py      # CSV 기반 저장/중복 판정/조회
    aggregation.py      # 정문+후문 합산, baseline, 통계
    congestion.py       # 오늘자 혼잡도 예측 로직
  routers/
    upload.py     # POST /api/v1/upload  — 원본 파일 업로드/전처리/적재
    congestion.py # GET  /api/v1/congestion/today
    stats.py      # GET  /api/v1/stats?date=YYYY-MM-DD
    meta.py       # GET  /api/v1/meta
    dashboard.py  # GET  /api/v1/dashboard/{daily,hourly,weekday,monthly}
data/
  raw/            # 원본 파일 임시 보관용 (git에는 커밋하지 않음)
  processed/      # 표준 CSV 저장 위치 (git에는 커밋하지 않음)
```

## 원본 파일 컬럼에 대한 가정

`preprocessing.py`는 아래 형태를 가정해 컬럼을 정규식으로 자동 탐지합니다.

- 날짜 컬럼: `날짜` / `수집일자` / `date` 중 하나
- 게이트명 컬럼: `게이트` / `게이트명` / `gate` 중 하나 (값: `자료실.정문`, `자료실.후문`)
- 통로ID 컬럼: `통로ID` / `passage_id` 중 하나
- 시간대별 IN/OUT 컬럼: `8_IN`, `8_OUT`, `08시_IN` 처럼 `{시간}_{IN|OUT}` 형태 (8~23시)

실제 원본 파일의 컬럼명이 다르면 `app/services/preprocessing.py`의
`_DATE_COL_CANDIDATES`, `_GATE_COL_CANDIDATES`, `_PASSAGE_COL_CANDIDATES`,
`_HOUR_COL_PATTERN`만 실제 컬럼명에 맞게 수정하면 됩니다.

## 전처리 규칙

- 날짜를 `YYYY-MM-DD`로 통일 (`YYYY/MM/DD`, `YYYY.MM.DD`, `YYYYMMDD` 등도 자동 인식)
- `자료실.정문` → `front`, `자료실.후문` → `back`
- 시간은 8~23 정수로 저장, IN/OUT은 정수로 변환
- 빈 셀 / 숫자 변환 불가 / 음수 값은 저장하지 않고 업로드 응답의 `errors` 목록에 기록
- 같은 `date + gate + hour` 조합이 이미 있으면 자동 합산하지 않고 중복으로 표시, 집계 시 제외
- 최신 날짜가 오늘(서버 로컬 날짜)과 같으면 `is_partial=true`
- 결측값을 임의로 0으로 채우지 않음

## 집계 규칙

- `visit_count = front.in_count + back.in_count` (MVP는 IN 기준)
- `baseline_avg`: 같은 요일·같은 시간대의 직전 4주 평균 (데이터 부족 시 있는 만큼만 사용, 전혀 없으면 `null`)
- `difference_rate`: `(실제값 - baseline_avg) / baseline_avg * 100`
- `congestion_score`: 해당 시간대의 과거 분포 내 백분위(0~100)
- `congestion_level`: 하위 35% 이하 `quiet`, 35~70% `normal`, 70% 초과 `busy`
  (분위수 기준은 `app/core/config.py`의 `CONGESTION_QUANTILE_LOW/HIGH`에서 조정 가능)

## API 요약

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/v1/upload` | 원본 엑셀/CSV 업로드 → 전처리 → 표준 CSV 적재 |
| GET | `/api/v1/congestion/today` | 오늘의 예상 혼잡도 + 시간대별 예측 |
| GET | `/api/v1/stats?date=YYYY-MM-DD` | 특정 날짜 실측/집계 데이터 |
| GET | `/api/v1/meta` | 도서관명, 운영 시간대, 혼잡도 라벨 등 기준정보 |
| GET | `/api/v1/dashboard/daily` | 날짜별 총 입장량 |
| GET | `/api/v1/dashboard/hourly` | 시간대별 입장량 합계 |
| GET | `/api/v1/dashboard/weekday` | 요일별 평균 입장량 |
| GET | `/api/v1/dashboard/monthly` | 월별 평균 입장량 |

모든 오류는 다음 형태로 반환됩니다.

```json
{ "error": { "code": "DATA_NOT_FOUND", "message": "..." } }
```

코드: `DATA_NOT_FOUND`(404), `INVALID_DATE`(400), `EXCEL_FORMAT_ERROR`(422), `PROCESSING_ERROR`(500)

## 자주 겪는 오류

| 증상 | 원인 | 해결 |
|---|---|---|
| `Could not import module "main"` | 잘못된 폴더에서 실행 / 잘못된 명령 | `app` 폴더가 보이는 프로젝트 루트에서 `uvicorn app.main:app --reload` 실행 |
| `ModuleNotFoundError: No module named 'app.core.xxx'` | 파일을 개별 다운로드하면서 `errors (2).py`처럼 이름이 바뀜 | 저장소를 통째로 `git clone`해서 사용 (파일 개별 다운로드 지양) |
| `ImportError: cannot import name 'XXX'` | `__pycache__`에 남은 옛 `.pyc` 캐시 | 프로젝트 전체에서 `__pycache__` 폴더 삭제 후 재실행 |
| `str | None` 관련 문법에서 `TypeError` | Python 3.10 미만 사용 | Python 3.10 이상으로 업그레이드 (요구 사항 참고) |