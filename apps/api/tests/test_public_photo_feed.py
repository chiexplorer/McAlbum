"""使用 MySQL 实际类型验证照片时间流的月份边界与游标分页。"""

import hashlib
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.database import engine
from app.models import MediaAsset, MediaVariant, Photo, User
from app.repositories.content import ContentRepository
from app.services.public_content import PublicContentService


def test_photo_feed_uses_beijing_month_and_stable_cursor() -> None:
    """北京时间跨月、标签筛选和下一页游标应共同保持稳定。"""

    marker = uuid4().hex
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection, expire_on_commit=False)
        try:
            user = User(
                id=f"usr_{marker}",
                username=f"feed-{marker}",
                display_name="时间流测试用户",
                password_hash="not-used",
                role_id="role-user",
                status="active",
                minecraft_name=None,
                application_reason="测试账号",
                review_reason=None,
                reviewed_at=None,
                reviewed_by=None,
                banned_at=None,
                banned_by=None,
                ban_reason=None,
                player_id=None,
                created_at=datetime.now(UTC).replace(tzinfo=None),
                updated_at=datetime.now(UTC).replace(tzinfo=None),
            )
            session.add(user)
            session.flush()

            photos = [
                _photo_fixture(
                    marker,
                    user.id,
                    "newer",
                    datetime(2099, 10, 20, 8, 0),
                    ["时间流测试"],
                ),
                # 2099-09-30 16:30 UTC 在北京已经进入十月。
                _photo_fixture(
                    marker,
                    user.id,
                    "boundary",
                    datetime(2099, 9, 30, 16, 30),
                    ["时间流测试"],
                ),
                # 2099-10-31 16:30 UTC 在北京已经进入十一月。
                _photo_fixture(
                    marker,
                    user.id,
                    "next-month",
                    datetime(2099, 10, 31, 16, 30),
                    ["时间流测试"],
                ),
                _photo_fixture(
                    marker,
                    user.id,
                    "tie-a",
                    datetime(2099, 12, 10, 8, 0),
                    ["时间流测试"],
                ),
                _photo_fixture(
                    marker,
                    user.id,
                    "tie-z",
                    datetime(2099, 12, 10, 8, 0),
                    ["时间流测试"],
                ),
            ]
            for asset, variant, photo, _tags in photos:
                session.add_all([asset, variant, photo])
            session.flush()
            content_repo = ContentRepository(session)
            for _asset, _variant, photo, tag_names in photos:
                content_repo.replace_photo_tags(
                    photo.id,
                    tag_names,
                    datetime.now(UTC).replace(tzinfo=None),
                )
            session.flush()

            service = PublicContentService(session)
            first = service.list_photo_feed(
                limit=1,
                month="2099-10",
                tag="时间流测试",
            )
            assert [item.photo.id for item in first.items] == [photos[0][2].id]
            assert first.items[0].asset.original_url == (
                f"/originals/test/{photos[0][0].id}.png"
            )
            assert first.has_more is True
            assert first.next_cursor is not None

            second = service.list_photo_feed(
                limit=1,
                before=datetime.fromisoformat(first.next_cursor.captured_at),
                before_id=first.next_cursor.id,
                month="2099-10",
                tag="时间流测试",
            )
            assert [item.photo.id for item in second.items] == [photos[1][2].id]
            assert second.has_more is False
            assert second.next_cursor is None

            tied_first = service.list_photo_feed(
                limit=1,
                month="2099-12",
                tag="时间流测试",
            )
            assert [item.photo.id for item in tied_first.items] == [photos[4][2].id]
            assert tied_first.next_cursor is not None
            tied_second = service.list_photo_feed(
                limit=1,
                before=datetime.fromisoformat(tied_first.next_cursor.captured_at),
                before_id=tied_first.next_cursor.id,
                month="2099-12",
                tag="时间流测试",
            )
            assert [item.photo.id for item in tied_second.items] == [photos[3][2].id]

            timeline = service.photo_timeline("时间流测试")
            assert [(item.key, item.count) for item in timeline] == [
                ("2099-12", 2),
                ("2099-11", 1),
                ("2099-10", 2),
            ]
        finally:
            session.close()
            transaction.rollback()


def _photo_fixture(
    marker: str,
    owner_id: str,
    suffix: str,
    captured_at: datetime,
    tags: list[str],
) -> tuple[MediaAsset, MediaVariant, Photo, list[str]]:
    """构造同一事务内可公开读取的媒体、变体与照片。"""

    now = datetime.now(UTC).replace(tzinfo=None)
    asset_id = f"media-{marker}-{suffix}"
    photo_id = f"photo-{marker}-{suffix}"
    asset = MediaAsset(
        id=asset_id,
        owner_user_id=owner_id,
        original_filename=f"{suffix}.png",
        storage_key=f"originals/test/{asset_id}.png",
        mime_type="image/png",
        extension="png",
        byte_size=100,
        width=1600,
        height=900,
        sha256=hashlib.sha256(f"original-{marker}-{suffix}".encode()).hexdigest(),
        captured_at=captured_at,
        alt_text=f"{suffix} 测试照片",
        focal_x=0.5,
        focal_y=0.5,
        processing_status="ready",
        editorial_status="draft",
        allow_original_download=False,
        created_at=now,
        updated_at=now,
    )
    variant = MediaVariant(
        asset_id=asset_id,
        name="w960",
        storage_key=f"variants/test/{asset_id}/w960.webp",
        mime_type="image/webp",
        byte_size=50,
        width=960,
        height=540,
        sha256=hashlib.sha256(f"variant-{marker}-{suffix}".encode()).hexdigest(),
    )
    photo = Photo(
        id=photo_id,
        title=f"{suffix} 测试照片",
        description="验证按拍摄时间组织的公开照片时间流。",
        asset_id=asset_id,
        captured_at=captured_at,
        photographer_id=None,
        featured=False,
        display_variant="normal",
        status="published",
        author_user_id=owner_id,
        published_at=now,
        published_by=owner_id,
        rejection_reason=None,
        created_at=now,
        updated_at=now,
    )
    return asset, variant, photo, tags
