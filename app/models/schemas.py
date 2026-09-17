"""문서의 2/3/6절 규격에 대응하는 Pydantic 스키마"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Gate = Literal["front", "back"]
Level = Literal["quiet", "normal", "busy"]


# ---------- 2. 전처리 표준 출력 규격 ----------
class StandardRecord(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    day_of_week: str
    gate: Gate
    gate_name: str
    passage_id: str
    hour: int = Field(..., ge=8, le=23)
    in_count: int
    out_count: int
    total_in: int
    total_out: int
    is_partial: bool
    source_file: str


class PreprocessError(BaseModel):
    source_file: str
    row_ref: str
    reason: str
    raw_value: Optional[str] = None


class UploadResult(BaseModel):
    inserted_rows: int
    duplicate_rows: int
    error_rows: int
    is_partial_latest_date: bool
    errors: list[PreprocessError] = []


# ---------- 3. 팀 내부 공통 집계 규격 ----------
class HourlyAggregate(BaseModel):
    date: str
    hour: int
    in_count: int
    out_count: int
    visit_count: int
    baseline_avg: Optional[float] = None
    difference_rate: Optional[float] = None
    congestion_score: Optional[float] = None
    congestion_level: Optional[Level] = None
    is_partial: bool


# ---------- 6. API 공통 규격 ----------
class CongestionNow(BaseModel):
    level: Level
    label: str
    score: float


class Recommendation(BaseModel):
    best_start_hour: int
    best_end_hour: int
    message: str


class TodayHourly(BaseModel):
    hour: int
    expected_visitors: int
    baseline_avg: Optional[float] = None
    difference_rate: Optional[float] = None
    level: Optional[Level] = None


class TodayCongestionResponse(BaseModel):
    date: str
    data_status: Literal["forecast", "actual", "partial"]
    reference_time: str
    congestion: CongestionNow
    recommendation: Recommendation
    hourly: list[TodayHourly]
    updated_at: str


class StatsHourly(BaseModel):
    hour: int
    in_count: int
    out_count: int


class StatsResponse(BaseModel):
    date: str
    data_status: Literal["forecast", "actual", "partial"]
    total_in: int
    total_out: int
    hourly: list[StatsHourly]


class MetaResponse(BaseModel):
    library_name: str
    available_hours: list[int]
    levels: dict[str, str]


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
