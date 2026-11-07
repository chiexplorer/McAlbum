"""使用 MySQL 验证缺失媒体扫描与可恢复清理。"""

import hashlib
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.database import engine
from app.models import MediaAsset, MediaVariant, Photo, Player, Story, User
from app.services.media_integrity import MediaIntegrityService


def test_missing_media_isolated_without_hard_delete() -> None:
    marker = uuid4().hex
    now = datetime.now(UTC).replace(tzinfo=None)
    with engine.connect() as connection:
        transaction = connection.begin()
        db = Session(bind=connection, expire_on_commit=False)
        try:
            user = User(
                id=f"usr_{marker}", username=f"media-audit-{marker}",
                display_name="媒体检查用户", password_hash="not-used",
                role_id="role-user", status="active", minecraft_name=None,
                application_reason="测试账号", review_reason=None,
                reviewed_at=None, reviewed_by=None, banned_at=None, banned_by=None,
                ban_reason=None, player_id=None, created_at=now, updated_at=now,
            )
            db.add(user)
            db.flush()
            asset = MediaAsset(
                id=f"media-{marker}", owner_user_id=user.id,
                original_filename="missing.png",
                storage_key=f"originals/test/{marker}.png", mime_type="image/png",
                extension="png", byte_size=100, width=1600, height=900,
                sha256=hashlib.sha256(marker.encode()).hexdigest(), captured_at=now,
                alt_text="不存在的测试图片", focal_x=0.5, focal_y=0.5,
                processing_status="ready", editorial_status="draft",
                allow_original_download=False, created_at=now, updated_at=now,
            )
            db.add(asset)
            db.flush()
            db.add_all([
                MediaVariant(
                    asset_id=asset.id, name="w960",
                    storage_key=f"variants/test/{marker}/w960.webp",
                    mime_type="image/webp", byte_size=50, width=960, height=540,
                    sha256=hashlib.sha256(f"variant-{marker}".encode()).hexdigest(),
                ),
                Player(
                    id=f"player-{marker}", name="测试玩家", bio="", status="private",
                    avatar_asset_id=asset.id, joined_at=None, created_at=now, updated_at=now,
                ),
                Photo(
                    id=f"photo-{marker}", title="缺图照片", description="",
                    asset_id=asset.id, captured_at=now, photographer_id=None,
                    featured=False, display_variant="normal", status="published",
                    author_user_id=user.id, published_at=now, published_by=user.id,
                    rejection_reason=None, created_at=now, updated_at=now,
                ),
                Story(
                    id=f"story-{marker}", title="缺图作品集", summary="测试",
                    cover_asset_id=asset.id,
                    sections=[{"id": "section-test", "type": "wide-image",
                               "assetId": asset.id}],
                    status="published", author_user_id=user.id, published_at=now,
                    published_by=user.id, rejection_reason=None,
                    created_at=now, updated_at=now,
                ),
            ])
            db.flush()

            service = MediaIntegrityService(db)
            report = service.scan()
            assert [item.asset_id for item in report.invalid_media] == [asset.id]
            assert report.photo_ids == [f"photo-{marker}"]
            assert report.story_ids == [f"story-{marker}"]
            assert report.player_ids == [f"player-{marker}"]

            service.apply(report, user.id)
            db.flush()
            assert asset.processing_status == "failed"
            assert db.get(Photo, f"photo-{marker}").status == "deleted"
            assert db.get(Story, f"story-{marker}").status == "deleted"
            assert db.get(Player, f"player-{marker}").avatar_asset_id is None
        finally:
            db.close()
            transaction.rollback()
