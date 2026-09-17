from fastapi import APIRouter

from app.models.schemas import TodayCongestionResponse
from app.services.congestion import build_today_forecast

router = APIRouter(prefix="/api/v1", tags=["congestion"])


@router.get("/congestion/today", response_model=TodayCongestionResponse)
def get_today_congestion():
    """오늘의 예상 혼잡도와 시간대별 정보를 반환합니다."""
    return build_today_forecast()
