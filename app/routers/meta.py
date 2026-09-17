from fastapi import APIRouter

from app.core.config import AVAILABLE_HOURS, LEVEL_LABELS, LIBRARY_NAME
from app.models.schemas import MetaResponse

router = APIRouter(prefix="/api/v1", tags=["meta"])


@router.get("/meta", response_model=MetaResponse)
def get_meta():
    """프론트에서 사용할 서비스 기준정보를 반환합니다."""
    return MetaResponse(
        library_name=LIBRARY_NAME,
        available_hours=AVAILABLE_HOURS,
        levels=LEVEL_LABELS,
    )
