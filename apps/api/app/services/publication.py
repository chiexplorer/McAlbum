"""把已审核数据库内容投影回静态内容源并触发 Nuxt 重建。"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Comment, MediaAsset, MediaVariant, Photo, Story, User
from app.services.auth import AuthService, Principal
from app.services.content import ContentService

PROJECT_ROOT = Path(__file__).resolve().parents[4]
CONTENT_ROOT = PROJECT_ROOT / "content"


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        json.dump(value, temporary, ensure_ascii=False, indent=2)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, path)


def beijing_iso(value: Any) -> str:
    """把数据库中的无时区 UTC 时间转换为带 +08:00 的公开时间。"""

    from zoneinfo import ZoneInfo

    return (
        value.replace(tzinfo=UTC)
        .astimezone(ZoneInfo("Asia/Shanghai"))
        .isoformat(timespec="seconds")
    )


class PublicationService:
    """在管理员明确操作时输出公开 JSON，并同步执行静态构建。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    def rebuild(self, principal: Principal) -> dict[str, object]:
        AuthService.require(principal, "snapshot.publish")
        if not self.settings.enable_build_trigger:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "静态重建未启用；请设置 MCALBUM_ENABLE_BUILD_TRIGGER=true",
            )
        counts = self.export_published()
        environment = os.environ.copy()
        environment["MCALBUM_PUBLISHED_ONLY"] = "1"
        command = "npm.cmd" if os.name == "nt" else "npm"
        completed = subprocess.run(
            [command, "run", "generate:web"],
            cwd=PROJECT_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        if completed.returncode != 0:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"message": "静态重建失败", "output": completed.stderr[-3000:]},
            )
        AuthService(self.db).audit(principal.user.id, "site.rebuild", "site", "public", counts)
        self.db.commit()
        return {"status": "ready", "counts": counts, "output": completed.stdout[-1000:]}

    def export_published(self) -> dict[str, int]:
        """把数据库公开内容同步为静态快照，并移除已失效的旧 JSON。"""

        content = ContentService(self.db)
        media = list(
            self.db.scalars(select(MediaAsset).where(MediaAsset.processing_status == "ready"))
        )
        photos = list(self.db.scalars(select(Photo).where(Photo.status == "published")))
        stories = list(self.db.scalars(select(Story).where(Story.status == "published")))
        self._prune_collection("media-assets", {item.id for item in media})
        self._prune_collection("photos", {item.id for item in photos})
        self._prune_collection("stories", {item.id for item in stories})
        for asset in media:
            variants = list(
                self.db.scalars(select(MediaVariant).where(MediaVariant.asset_id == asset.id))
            )
            write_json_atomic(
                CONTENT_ROOT / "media-assets" / f"{asset.id}.json",
                {
                    "$schema": "../../contracts/json-schema/media-asset.schema.json",
                    "id": asset.id,
                    "originalFilename": asset.original_filename,
                    "storageKey": asset.storage_key,
                    "mimeType": asset.mime_type,
                    "extension": asset.extension,
                    "byteSize": asset.byte_size,
                    "width": asset.width,
                    "height": asset.height,
                    "sha256": asset.sha256,
                    "capturedAt": beijing_iso(asset.captured_at),
                    "timeZone": "Asia/Shanghai",
                    "altText": asset.alt_text,
                    "focalPoint": {"x": float(asset.focal_x), "y": float(asset.focal_y)},
                    "editorialStatus": asset.editorial_status,
                    "processingStatus": asset.processing_status,
                    "allowOriginalDownload": asset.allow_original_download,
                    "variants": [
                        {
                            "name": item.name,
                            "storageKey": item.storage_key,
                            "mimeType": item.mime_type,
                            "byteSize": item.byte_size,
                            "width": item.width,
                            "height": item.height,
                            "sha256": item.sha256,
                        }
                        for item in variants
                    ],
                    "importedAt": asset.created_at.replace(tzinfo=UTC).isoformat(
                        timespec="seconds"
                    ),
                },
            )
        for photo in photos:
            projection = content.serialize("photo", photo)
            comments = self._public_comments(photo.id)
            write_json_atomic(
                CONTENT_ROOT / "photos" / f"{photo.id}.json",
                {
                    "$schema": "../../contracts/json-schema/photo.schema.json",
                    "id": photo.id,
                    "title": photo.title,
                    "description": photo.description,
                    "assetId": photo.asset_id,
                    "capturedAt": beijing_iso(photo.captured_at),
                    "timeZone": "Asia/Shanghai",
                    "photographerId": photo.photographer_id,
                    "playerIds": projection["player_ids"],
                    "storyIds": projection["story_ids"],
                    "tags": projection["tags"],
                    "status": "published",
                    "isMock": False,
                    "featured": photo.featured,
                    "displayVariant": photo.display_variant,
                    "comments": comments,
                },
            )
        for story in stories:
            projection = content.serialize("story", story)
            write_json_atomic(
                CONTENT_ROOT / "stories" / f"{story.id}.json",
                {
                    "$schema": "../../contracts/json-schema/story.schema.json",
                    "id": story.id,
                    "title": story.title,
                    "summary": story.summary,
                    "coverAssetId": story.cover_asset_id,
                    "playerIds": projection["player_ids"],
                    "sections": story.sections,
                    "status": "published",
                    "isMock": False,
                },
            )
        return {
            "media": len(media),
            "photos": len(photos),
            "stories": len(stories),
        }

    @staticmethod
    def _prune_collection(collection: str, retained_ids: set[str]) -> None:
        """仅删除指定内容集合中不再公开的 JSON 快照。"""

        directory = CONTENT_ROOT / collection
        for path in directory.glob("*.json"):
            if path.stem not in retained_ids:
                path.unlink()

    def _public_comments(self, photo_id: str) -> list[dict[str, object]]:
        rows = self.db.execute(
            select(Comment, User)
            .join(User, User.id == Comment.author_user_id)
            .where(
                Comment.photo_id == photo_id,
                Comment.status == "published",
                User.player_id.is_not(None),
            )
        )
        return [
            {
                "id": comment.id.replace("_", "-")[:100],
                "authorPlayerId": user.player_id,
                "body": comment.body,
                "status": "published",
                "createdAt": comment.created_at.replace(tzinfo=UTC).isoformat(timespec="seconds"),
            }
            for comment, user in rows
        ]
