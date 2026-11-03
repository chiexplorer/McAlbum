"""服务健康检查。"""

from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """返回不依赖数据库的进程健康状态。"""

    return HealthResponse(status="ok", service="mcalbum-api")
