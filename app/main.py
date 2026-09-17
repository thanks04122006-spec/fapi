from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.errors import register_error_handlers
from app.routers import congestion, dashboard, meta, stats, upload

app = FastAPI(
    title="용산꿈나무도서관API",
    description="도서관 방문자 데이터를 기반으로 시간대별 혼잡도를 안내하는 백엔드 API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 단계 기본값. 배포 시 프론트 도메인으로 제한 필요.
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

app.include_router(upload.router)
app.include_router(congestion.router)
app.include_router(stats.router)
app.include_router(meta.router)
app.include_router(dashboard.router)


@app.get("/")
def root():
    return {"service": "library-congestion-api", "status": "ok"}
