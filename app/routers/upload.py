from fastapi import APIRouter, File, UploadFile

from app.core.errors import ProcessingError
from app.models.schemas import UploadResult
from app.services import data_store, preprocessing

router = APIRouter(prefix="/api/v1", tags=["upload"])


@router.post("/upload", response_model=UploadResult)
async def upload_raw_file(file: UploadFile = File(...)):
    """원본 방문자수 엑셀/CSV 파일을 업로드하여 표준 세로형으로 변환 후 적재합니다."""
    content = await file.read()
    try:
        raw_df = preprocessing.read_raw_file(content, file.filename)
        records, errors = preprocessing.preprocess_dataframe(raw_df, source_file=file.filename)
        inserted, duplicate = data_store.append_records(records)
    except Exception as e:
        if hasattr(e, "code"):
            raise
        raise ProcessingError(f"업로드 처리 중 오류가 발생했습니다: {e}")

    is_partial_latest = any(r.is_partial for r in records)

    return UploadResult(
        inserted_rows=inserted,
        duplicate_rows=duplicate,
        error_rows=len(errors),
        is_partial_latest_date=is_partial_latest,
        errors=errors,
    )
