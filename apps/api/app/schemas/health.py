"""健康检查响应模型。"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """API 进程健康状态。"""

    status: str
    service: str
