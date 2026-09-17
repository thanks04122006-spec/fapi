"""4. 기본 통계 담당 출력 규격에 대응하는 보조 라우터

공식 API 규격(6절)에는 없지만, 팀 내부 통계 화면/대시보드용으로 자주 쓰이는
날짜별/시간대별/요일별/월별 집계를 제공합니다.
"""
from fastapi import APIRouter

from app.services import aggregation

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/daily")
def daily_totals():
    """날짜별 총 입장량"""
    return aggregation.daily_totals().to_dict(orient="records")


@router.get("/hourly")
def hourly_totals():
    """시간대별 입장량(전체 기간 합계)"""
    return aggregation.hourly_totals().to_dict(orient="records")


@router.get("/weekday")
def weekday_averages():
    """요일별 평균 입장량"""
    return aggregation.weekday_averages().to_dict(orient="records")


@router.get("/monthly")
def monthly_averages():
    """월별 평균 입장량"""
    return aggregation.monthly_averages().to_dict(orient="records")
