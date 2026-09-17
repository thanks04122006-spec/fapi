"""서비스 전역 설정값"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
STANDARD_CSV_PATH = PROCESSED_DIR / "standard_long.csv"
ERROR_LOG_CSV_PATH = PROCESSED_DIR / "preprocessing_errors.csv"

LIBRARY_NAME = "용산꿈나무도서관"
AVAILABLE_HOURS = list(range(8, 24))  # 8~23
LEVEL_LABELS = {"quiet": "여유", "normal": "보통", "busy": "혼잡"}

GATE_NAME_MAP = {
    "자료실.정문": "front",
    "자료실.후문": "back",
}

# 혼잡도 3단계 분위수 기준 (T04 담당자가 조정 가능, 값 이름은 유지)
CONGESTION_QUANTILE_LOW = 0.35
CONGESTION_QUANTILE_HIGH = 0.70

# baseline: 같은 요일 · 같은 시간대의 직전 N주 평균
BASELINE_WEEKS = 4

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
