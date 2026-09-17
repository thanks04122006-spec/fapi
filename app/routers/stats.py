from datetime import datetime

from fastapi import APIRouter, Query

from app.core.errors import DataNotFoundError, InvalidDateError
from app.models.schemas import StatsHourly, StatsResponse
from app.services import aggregation

router = APIRouter(prefix="/api/v1", tags=["stats"])


@router.get("/stats", response_model=StatsResponse)
def get_stats(date: str = Query(..., description="YYYY-MM-DD")):
    """선택한 날짜의 실제/집계 데이터를 반환합니다."""
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise InvalidDateError()

    day_rows = aggregation.build_hourly_aggregates_for_date(date)
    if day_rows.empty:
        raise DataNotFoundError()

    total_in = int(day_rows["in_count"].sum())
    total_out = int(day_rows["out_count"].sum())
    is_partial = bool(day_rows["is_partial"].any())

    hourly = [
        StatsHourly(hour=int(r["hour"]), in_count=int(r["in_count"]), out_count=int(r["out_count"]))
        for _, r in day_rows.iterrows()
    ]

    return StatsResponse(
        date=date,
        data_status="partial" if is_partial else "actual",
        total_in=total_in,
        total_out=total_out,
        hourly=hourly,
    )
