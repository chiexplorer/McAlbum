"""数据库迁移后使用的管理员初始化与静态内容导入命令。"""

from __future__ import annotations

import argparse
import getpass
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password, utc_now
from app.models import (
    MediaAsset,
    MediaVariant,
    Photo,
    PhotoStoryLink,
    Story,
    User,
)
from app.repositories.content import ContentRepository

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def json_files(collection: str) -> list[dict[str, object]]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((PROJECT_ROOT / "content" / collection).glob("*.json"))
    ]


def parse_datetime(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        raise ValueError(f"时间缺少时区：{value}")
    return parsed.astimezone(UTC).replace(tzinfo=None)


def create_admin(username: str, display_name: str) -> None:
    """交互读取密码并创建首个管理员，不把秘密留在命令历史中。"""

    password = getpass.getpass("管理员密码（至少 12 位）：")
    confirmation = getpass.getpass("再次输入管理员密码：")
    if password != confirmation or len(password) < 12:
        raise SystemExit("密码不一致或少于 12 位")
    normalized = username.strip().lower()
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.username == normalized)):
            raise SystemExit("用户名已存在")
        now = utc_now()
        db.add(
            User(
                id=f"usr_{uuid4().hex}",
                username=normalized,
                display_name=display_name.strip(),
                password_hash=hash_password(password),
                role="admin",
                enabled=True,
                player_id=None,
                created_at=now,
                updated_at=now,
            )
        )
        db.commit()
    print(f"管理员 {normalized} 已创建")


def import_content(owner_username: str) -> None:
    """幂等导入现有 JSON 媒体、照片和作品集，作为协作阶段初始数据。"""

    with SessionLocal() as db:
        owner = db.scalar(select(User).where(User.username == owner_username.strip().lower()))
        if owner is None or owner.role != "admin":
            raise SystemExit("导入账号不存在或不是管理员")
        now = utc_now()
        media_count = 0
        for item in json_files("media-assets"):
            asset_id = str(item["id"])
            if db.get(MediaAsset, asset_id):
                continue
            asset = MediaAsset(
                id=asset_id,
                owner_user_id=owner.id,
                original_filename=str(item["originalFilename"]),
                storage_key=str(item["storageKey"]),
                mime_type=str(item["mimeType"]),
                extension=str(item["extension"]),
                byte_size=int(item["byteSize"]),
                width=int(item["width"]),
                height=int(item["height"]),
                sha256=str(item["sha256"]),
                captured_at=parse_datetime(item["capturedAt"]),
                alt_text=str(item["altText"]),
                focal_x=float(item["focalPoint"]["x"]),  # type: ignore[index]
                focal_y=float(item["focalPoint"]["y"]),  # type: ignore[index]
                processing_status=str(item["processingStatus"]),
                editorial_status=str(item["editorialStatus"]),
                allow_original_download=bool(item["allowOriginalDownload"]),
                created_at=parse_datetime(item["importedAt"]),
                updated_at=now,
            )
            db.add(asset)
            db.flush()
            for variant in item["variants"]:  # type: ignore[union-attr]
                db.add(
                    MediaVariant(
                        asset_id=asset_id,
                        name=str(variant["name"]),
                        storage_key=str(variant["storageKey"]),
                        mime_type=str(variant["mimeType"]),
                        byte_size=int(variant["byteSize"]),
                        width=int(variant["width"]),
                        height=int(variant["height"]),
                        sha256=str(variant["sha256"]),
                    )
                )
            media_count += 1

        photo_count = 0
        for item in json_files("photos"):
            item_id = str(item["id"])
            if db.get(Photo, item_id):
                continue
            db.add(
                Photo(
                    id=item_id,
                    title=str(item["title"]),
                    description=str(item["description"]),
                    asset_id=str(item["assetId"]),
                    captured_at=parse_datetime(item["capturedAt"]),
                    photographer_id=item.get("photographerId"),
                    featured=bool(item.get("featured", False)),
                    display_variant=str(item.get("displayVariant", "normal")),
                    status=str(item["status"]),
                    author_user_id=owner.id,
                    published_at=None,
                    published_by=None,
                    rejection_reason=None,
                    created_at=now,
                    updated_at=now,
                )
            )
            photo_count += 1

        story_count = 0
        for item in json_files("stories"):
            item_id = str(item["id"])
            if db.get(Story, item_id):
                continue
            db.add(
                Story(
                    id=item_id,
                    title=str(item["title"]),
                    summary=str(item["summary"]),
                    cover_asset_id=str(item["coverAssetId"]),
                    sections=item["sections"],
                    status=str(item["status"]),
                    author_user_id=owner.id,
                    published_at=None,
                    published_by=None,
                    rejection_reason=None,
                    created_at=now,
                    updated_at=now,
                )
            )
            story_count += 1

        db.flush()
        content_repo = ContentRepository(db)
        for item in json_files("photos"):
            photo_id = str(item["id"])
            content_repo.replace_photo_tags(
                photo_id,
                [str(tag) for tag in item.get("tags", [])],
                now,
            )
            for story_id in item.get("storyIds", []):
                if db.get(Story, story_id):
                    db.merge(PhotoStoryLink(photo_id=photo_id, story_id=story_id))
        db.commit()
    summary = f"媒体 {media_count}、照片 {photo_count}、作品集 {story_count}"
    print(f"导入完成：{summary}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    admin = subparsers.add_parser("create-admin")
    admin.add_argument("--username", required=True)
    admin.add_argument("--display-name", required=True)
    importer = subparsers.add_parser("import-content")
    importer.add_argument("--owner", required=True, help="接收现有内容归属的管理员用户名")
    args = parser.parse_args()
    if args.command == "create-admin":
        create_admin(args.username, args.display_name)
    else:
        import_content(args.owner)


if __name__ == "__main__":
    main()
