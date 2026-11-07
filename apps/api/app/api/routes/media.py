"""已认证用户的媒体上传与浏览接口。"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.api.dependencies import CsrfPrincipal, Db, PrincipalDep
from app.core.rate_limit import limit
from app.repositories.content import ContentRepository
from app.schemas.content import MediaAssetResponse
from app.services.media import MediaService

router = APIRouter(prefix="/manage/media")
upload_limit = limit("media-upload", 20, 3600)
UploadLimited = Annotated[None, Depends(upload_limit)]


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
