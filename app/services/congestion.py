"""GET /api/v1/congestion/today 용 예측 로직

- 오늘 날짜에 대해 이미 수집된(is_partial) 시간대는 실측값을 사용합니다.
- 아직 지나지 않은 시간대는 baseline_avg(직전 4주 같은 요일·시간대 평균)를 예측값으로 사용합니다.
- 데이터가 전혀 없으면 DATA_NOT_FOUND 대신, 현재 시각 이전 시간대만 대상으로 비어있는 결과를 만듭니다.
"""
from __future__ import annotations

from datetime import datetime

from app.core.config import AVAILABLE_HOURS, LEVEL_LABELS
from app.services import aggregation, data_store


def build_today_forecast() -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    current_hour = datetime.now().hour

    df = data_store.load_non_duplicate()
    hourly_all = aggregation.hourly_gate_sum(df)
    today_rows = hourly_all[hourly_all["date"] == today]
    actual_by_hour = {int(r["hour"]): r for _, r in today_rows.iterrows()}

    hourly_result = []
    for hour in AVAILABLE_HOURS:
        baseline = aggregation.compute_baseline(hourly_all, today, hour)

        if hour in actual_by_hour:
            expected = int(actual_by_hour[hour]["visit_count"])
        elif baseline is not None:
            expected = int(round(baseline))
        else:
            expected = 0

        diff = aggregation.compute_difference_rate(expected, baseline)
        dist = aggregation._historical_distribution(hourly_all, hour, exclude_date=today)
        _, level = aggregation.compute_congestion(expected, dist)

        hourly_result.append(
            {
                "hour": hour,
                "expected_visitors": expected,
                "baseline_avg": baseline,
                "difference_rate": diff,
                "level": level,
            }
        )

    # 현재 시각 기준 혼잡도 (가장 가까운 시간대)
    current_hour_row = next((h for h in hourly_result if h["hour"] == current_hour), None)
    if current_hour_row is None:
        current_hour_row = hourly_result[0] if hourly_result else {"expected_visitors": 0, "level": "normal"}

    dist_now = aggregation._historical_distribution(hourly_all, current_hour_row["hour"] if "hour" in current_hour_row else current_hour, exclude_date=today)
    score_now, level_now = aggregation.compute_congestion(current_hour_row["expected_visitors"], dist_now)

    # 추천 시간대: quiet/normal 중 방문량이 가장 적은 연속 구간(가장 단순하게 예측치가 낮은 2시간)
    sorted_by_expected = sorted(hourly_result, key=lambda h: h["expected_visitors"])
    best_hour = sorted_by_expected[0]["hour"] if sorted_by_expected else AVAILABLE_HOURS[0]
    best_start, best_end = best_hour, min(best_hour + 2, AVAILABLE_HOURS[-1] + 1)

    return {
        "date": today,
        "data_status": "forecast" if not today_rows.empty else "partial",
        "reference_time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+09:00"),
        "congestion": {
            "level": level_now,
            "label": LEVEL_LABELS[level_now],
            "score": score_now,
        },
        "recommendation": {
            "best_start_hour": best_start,
            "best_end_hour": best_end,
            "message": f"오전 {best_start}시~{best_end}시 방문을 추천합니다."
            if best_start < 12
            else f"{best_start}시~{best_end}시 방문을 추천합니다.",
        },
        "hourly": hourly_result,
        "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+09:00"),
    }
