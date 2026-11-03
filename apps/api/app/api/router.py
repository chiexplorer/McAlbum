"""聚合所有 API 路由。"""

from fastapi import APIRouter

from app.api.routes.admin import router as admin_router
from app.api.routes.auth import router as auth_router
from app.api.routes.comments import router as comments_router
from app.api.routes.content import router as content_router
from app.api.routes.health import router as health_router
from app.api.routes.media import router as media_router
from app.api.routes.profiles import router as profiles_router
from app.api.routes.public_content import router as public_content_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["system"])
api_router.include_router(public_content_router, tags=["public-content"])
api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(media_router, tags=["media"])
api_router.include_router(content_router, tags=["content"])
api_router.include_router(profiles_router, tags=["profile"])
api_router.include_router(comments_router, tags=["comments"])
api_router.include_router(admin_router, tags=["admin"])
