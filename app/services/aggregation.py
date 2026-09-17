"""3. 팀 내부 공통 집계 규격 + 4. 기본 통계 + 5. 혼잡도 규격 구현"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from app.core.config import BASELINE_WEEKS, CONGESTION_QUANTILE_HIGH, CONGESTION_QUANTILE_LOW
from app.services import data_store


def hourly_gate_sum(df: pd.DataFrame) -> pd.DataFrame:
    """정문+후문 합쳐 date+hour 별 in/out 합계, visit_count, is_partial 생성.

    visit_count = front.in_count + back.in_count (in_count 사용, MVP 기준)
    """
    if df.empty:
        return pd.DataFrame(
            columns=["date", "hour", "in_count", "out_count", "visit_count", "is_partial"]
        )

    grouped = (
        df.groupby(["date", "hour"], as_index=False)
        .agg(in_count=("in_count", "sum"), out_count=("out_count", "sum"), is_partial=("is_partial", "any"))
    )
    grouped["visit_count"] = grouped["in_count"]  # MVP: visit_count 기준 = in_count
    return grouped.sort_values(["date", "hour"]).reset_index(drop=True)


def _same_weekday_hour_history(hourly: pd.DataFrame, target_date: str, hour: int, weeks: int) -> list[float]:
    """target_date보다 이전인, 같은 요일 · 같은 시간대의 최근 N주 visit_count 값들."""
    target_dt = datetime.strptime(target_date, "%Y-%m-%d")
    values: list[float] = []
    for w in range(1, weeks + 1):
        prev_date = (target_dt - timedelta(weeks=w)).strftime("%Y-%m-%d")
        row = hourly[(hourly["date"] == prev_date) & (hourly["hour"] == hour)]
        if not row.empty:
            values.append(float(row.iloc[0]["visit_count"]))
    return values


def compute_baseline(hourly: pd.DataFrame, target_date: str, hour: int) -> float | None:
    values = _same_weekday_hour_history(hourly, target_date, hour, BASELINE_WEEKS)
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def compute_difference_rate(actual: float, baseline: float | None) -> float | None:
    if baseline is None or baseline == 0:
        return None
    return round((actual - baseline) / baseline * 100, 1)


def _historical_distribution(hourly: pd.DataFrame, hour: int, exclude_date: str | None = None) -> np.ndarray:
    subset = hourly[hourly["hour"] == hour]
    if exclude_date:
        subset = subset[subset["date"] != exclude_date]
    return subset["visit_count"].to_numpy(dtype=float)


def compute_congestion(value: float, distribution: np.ndarray) -> tuple[float, str]:
    """해당 시간대 과거 분포 기준 분위수로 congestion_score(0~100), congestion_level 산출."""
    if distribution.size == 0:
        # 과거 데이터가 없으면 판정 불가 -> 중간값으로 처리
        return 50.0, "normal"

    # score: 분포 내 백분위(percentile rank), 0~100
    rank = float((distribution < value).sum()) / distribution.size * 100
    score = round(min(max(rank, 0), 100), 1)

    if score <= CONGESTION_QUANTILE_LOW * 100:
        level = "quiet"
    elif score <= CONGESTION_QUANTILE_HIGH * 100:
        level = "normal"
    else:
        level = "busy"
    return score, level


def build_hourly_aggregates_for_date(target_date: str) -> pd.DataFrame:
    """특정 날짜의 시간대별 집계(visit_count, baseline_avg, difference_rate, congestion) 생성."""
    df = data_store.load_non_duplicate()
    hourly_all = hourly_gate_sum(df)

    day_rows = hourly_all[hourly_all["date"] == target_date].copy()
    if day_rows.empty:
        return day_rows

    baselines = []
    diffs = []
    scores = []
    levels = []
    for _, row in day_rows.iterrows():
        hour = int(row["hour"])
        baseline = compute_baseline(hourly_all, target_date, hour)
        diff = compute_difference_rate(row["visit_count"], baseline)
        dist = _historical_distribution(hourly_all, hour, exclude_date=target_date)
        score, level = compute_congestion(row["visit_count"], dist)

        baselines.append(baseline)
        diffs.append(diff)
        scores.append(score)
        levels.append(level)

    day_rows["baseline_avg"] = baselines
    day_rows["difference_rate"] = diffs
    day_rows["congestion_score"] = scores
    day_rows["congestion_level"] = levels
    return day_rows.sort_values("hour").reset_index(drop=True)


def daily_totals() -> pd.DataFrame:
    """날짜별 총 입장량"""
    df = data_store.load_non_duplicate()
    hourly = hourly_gate_sum(df)
    if hourly.empty:
        return hourly
    return hourly.groupby("date", as_index=False).agg(total_in=("in_count", "sum"), total_out=("out_count", "sum"))


def hourly_totals() -> pd.DataFrame:
    """시간대별 입장량(전체 기간 합계)"""
    df = data_store.load_non_duplicate()
    hourly = hourly_gate_sum(df)
    if hourly.empty:
        return hourly
    return hourly.groupby("hour", as_index=False).agg(total_in=("in_count", "sum"))


def weekday_averages() -> pd.DataFrame:
    """요일별 평균 입장량"""
    df = data_store.load_non_duplicate()
    hourly = hourly_gate_sum(df)
    if hourly.empty:
        return hourly
    hourly = hourly.copy()
    hourly["day_of_week"] = pd.to_datetime(hourly["date"]).dt.strftime("%a")
    daily = hourly.groupby(["date", "day_of_week"], as_index=False).agg(total_in=("in_count", "sum"))
    return daily.groupby("day_of_week", as_index=False).agg(avg_in=("total_in", "mean"))


def monthly_averages() -> pd.DataFrame:
    """월별 평균 입장량"""
    df = data_store.load_non_duplicate()
    hourly = hourly_gate_sum(df)
    if hourly.empty:
        return hourly
    hourly = hourly.copy()
    hourly["month"] = pd.to_datetime(hourly["date"]).dt.strftime("%Y-%m")
    daily = hourly.groupby(["date", "month"], as_index=False).agg(total_in=("in_count", "sum"))
    return daily.groupby("month", as_index=False).agg(avg_in=("total_in", "mean"))
