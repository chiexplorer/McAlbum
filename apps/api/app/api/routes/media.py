"""已认证用户的媒体上传与浏览接口。"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.api.dependencies import CsrfPrincipal, Db, PrincipalDep
from app.core.config import get_settings
from app.core.rate_limit import check_limit
from app.repositories.content import ContentRepository
from app.schemas.content import MediaAssetResponse
from app.services.media import MediaService

router = APIRouter(prefix="/manage/media")


def check_upload_limit(principal: PrincipalDep) -> None:
    """按账号独立计算上传额度，管理员使用更高但仍有边界的限额。"""

    settings = get_settings()
    attempts = (
        settings.media_upload_limit_admin
        if principal.is_admin
        else settings.media_upload_limit_user
    )
    check_limit("media-upload-user", principal.user.id, attempts, 3600)


UploadLimited = Annotated[None, Depends(check_upload_limit)]


@router.get("", response_model=list[MediaAssetResponse])
def list_media(principal: PrincipalDep, db: Db) -> list[MediaAssetResponse]:
    service = MediaService(db)
    return [
        service.response(item)
        for item in ContentRepository(db).list_media(principal.user.id)
    ]


@router.post("", response_model=MediaAssetResponse, status_code=status.HTTP_201_CREATED)
def upload_media(
    principal: CsrfPrincipal,
    file: Annotated[UploadFile, File()],
    alt_text: Annotated[str, Form()],
    captured_at: Annotated[datetime, Form()],
    db: Db,
    _limited: UploadLimited,
    focal_x: Annotated[float, Form()] = 0.5,
    focal_y: Annotated[float, Form()] = 0.5,
) -> MediaAssetResponse:
    service = MediaService(db)
    asset = service.upload(principal, file, alt_text, captured_at, focal_x, focal_y)
    return service.response(asset)
