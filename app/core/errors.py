"""API 공통 오류 응답 규격

모든 오류는 다음 형태를 따릅니다.
{
  "error": {
    "code": "DATA_NOT_FOUND",
    "message": "..."
  }
}
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """서비스 공통 오류 베이스 클래스"""

    code = "PROCESSING_ERROR"
    status_code = 500

    def __init__(self, message: str, code: str | None = None, status_code: int | None = None):
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        super().__init__(message)


class DataNotFoundError(AppError):
    code = "DATA_NOT_FOUND"
    status_code = 404

    def __init__(self, message: str = "해당 날짜의 데이터를 찾을 수 없습니다."):
        super().__init__(message)


class InvalidDateError(AppError):
    code = "INVALID_DATE"
    status_code = 400

    def __init__(self, message: str = "날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식을 사용하세요."):
        super().__init__(message)


class ExcelFormatError(AppError):
    code = "EXCEL_FORMAT_ERROR"
    status_code = 422

    def __init__(self, message: str = "엑셀 파일 형식이 올바르지 않습니다."):
        super().__init__(message)


class ProcessingError(AppError):
    code = "PROCESSING_ERROR"
    status_code = 500

    def __init__(self, message: str = "데이터 처리 중 오류가 발생했습니다."):
        super().__init__(message)


def _error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content=_error_body("PROCESSING_ERROR", f"예상하지 못한 오류가 발생했습니다: {exc}"),
        )
