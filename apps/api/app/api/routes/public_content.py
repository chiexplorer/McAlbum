"""无需登录的公开只读内容接口。"""

import hashlib
import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from app.api.dependencies import Db
from app.schemas.public_content import (
    PublicPhotoDetail,
    PublicPhotoEntry,
    PublicPhotoFeed,
    PublicPhotoMonth,
    PublicStoryDetail,
    PublicStoryEntry,
)
from app.services.public_content import PublicContentService

router = APIRouter(prefix="/public")


def set_cache_headers(request: Request, response: Response, payload: Any) -> Response | None:
    """为动态公开内容提供可立即重验证的 ETag，不缓存过期发布状态。"""

    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    etag = f'"{hashlib.sha256(encoded.encode("utf-8")).hexdigest()}"'
    headers = {"Cache-Control": "no-cache", "ETag": etag}
    requested_etag = request.headers.get("if-none-match", "").removeprefix("W/").strip('"')
    if requested_etag == etag.strip('"'):
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
    response.headers.update(headers)
    return None


@router.get("/photos", response_model=list[PublicPhotoEntry])
def list_public_photos(request: Request, response: Response, db: Db) -> Any:
    entries = PublicContentService(db).list_photos()
    payload = [item.model_dump(by_alias=True) for item in entries]
    return set_cache_headers(request, response, payload) or payload


@router.get("/photos/feed", response_model=PublicPhotoFeed)
def list_public_photo_feed(
    request: Request,
    response: Response,
    db: Db,
    limit: int = Query(default=40, ge=1, le=100),
    before: datetime | None = None,
    before_id: str | None = Query(default=None, min_length=1, max_length=120),
    month: str | None = Query(
        default=None,
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        description="按 Asia/Shanghai 月份筛选，格式为 YYYY-MM",
    ),
    tag: str | None = Query(default=None, min_length=1, max_length=80),
) -> Any:
    """按拍摄时间倒序读取公开照片，使用时间与 ID 组成稳定游标。"""

    if (before is None) != (before_id is None):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "before 与 before_id 必须同时提供",
        )
    if before is not None and before.tzinfo is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "before 必须包含时区")
    if month is not None and not 1000 <= int(month[:4]) <= 9998:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "month 年份必须位于 1000 到 9998",
        )
    feed = PublicContentService(db).list_photo_feed(
        limit=limit,
        before=before,
        before_id=before_id,
        month=month,
        tag=tag,
    )
    payload = feed.model_dump(by_alias=True)
    return set_cache_headers(request, response, payload) or payload


@router.get("/photos/timeline", response_model=list[PublicPhotoMonth])
def get_public_photo_timeline(
    request: Request,
    response: Response,
    db: Db,
    tag: str | None = Query(default=None, min_length=1, max_length=80),
) -> Any:
    """按北京时间月份返回公开照片数量，用于月份导航。"""

    entries = PublicContentService(db).photo_timeline(tag)
    payload = [item.model_dump(by_alias=True) for item in entries]
    return set_cache_headers(request, response, payload) or payload


@router.get("/photos/{photo_id}", response_model=PublicPhotoDetail)
def get_public_photo(photo_id: str, request: Request, response: Response, db: Db) -> Any:
    detail = PublicContentService(db).get_photo(photo_id)
    if detail is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "照片不存在或尚未发布")
    payload = detail.model_dump(by_alias=True)
    return set_cache_headers(request, response, payload) or payload


@router.get("/stories", response_model=list[PublicStoryEntry])
def list_public_stories(request: Request, response: Response, db: Db) -> Any:
    entries = PublicContentService(db).list_stories()
    payload = [item.model_dump(by_alias=True) for item in entries]
    return set_cache_headers(request, response, payload) or payload


@router.get("/stories/{story_id}", response_model=PublicStoryDetail)
def get_public_story(story_id: str, request: Request, response: Response, db: Db) -> Any:
    detail = PublicContentService(db).get_story(story_id)
    if detail is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "作品集不存在或尚未发布")
    payload = detail.model_dump(by_alias=True)
    return set_cache_headers(request, response, payload) or payload
