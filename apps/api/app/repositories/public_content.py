"""公开内容的只读数据库访问边界。"""

from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    Comment,
    MediaAsset,
    MediaVariant,
    Photo,
    PhotoPlayerLink,
    PhotoStoryLink,
    PhotoTagLink,
    Player,
    Story,
    StoryPlayerLink,
    Tag,
    User,
)


class PublicContentRepository:
    """只返回已经发布且媒体处理完成的公开照片及其关系。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_photos(self) -> list[tuple[Photo, MediaAsset]]:
        rows = self.db.execute(
            select(Photo, MediaAsset)
            .join(MediaAsset, MediaAsset.id == Photo.asset_id)
            .where(Photo.status == "published", MediaAsset.processing_status == "ready")
            .order_by(Photo.captured_at.desc(), Photo.id.desc())
        )
        return list(rows.tuples())

    def list_photo_feed(
        self,
        *,
        limit: int,
        before: datetime | None = None,
        before_id: str | None = None,
        month_start: datetime | None = None,
        month_end: datetime | None = None,
        tag: str | None = None,
    ) -> tuple[list[tuple[Photo, MediaAsset]], bool]:
        """按拍摄时间和稳定 ID 倒序读取一页公开照片。"""

        conditions = [Photo.status == "published", MediaAsset.processing_status == "ready"]
        if before is not None and before_id is not None:
            conditions.append(
                or_(
                    Photo.captured_at < before,
                    and_(Photo.captured_at == before, Photo.id < before_id),
                )
            )
        if month_start is not None and month_end is not None:
            conditions.extend(
                [Photo.captured_at >= month_start, Photo.captured_at < month_end]
            )
        if tag:
            conditions.append(self._has_tag(tag))

        statement = (
            select(Photo, MediaAsset)
            .join(MediaAsset, MediaAsset.id == Photo.asset_id)
            .where(*conditions)
            .order_by(Photo.captured_at.desc(), Photo.id.desc())
            .limit(limit + 1)
        )
        rows = [(photo, asset) for photo, asset in self.db.execute(statement)]
        return rows[:limit], len(rows) > limit

    def photo_timeline(self, tag: str | None = None) -> list[tuple[str, int]]:
        """在 MySQL 中按北京时间月份汇总公开照片数量。"""

        month_key = func.date_format(
            func.convert_tz(Photo.captured_at, "+00:00", "+08:00"), "%Y-%m"
        )
        conditions = [Photo.status == "published", MediaAsset.processing_status == "ready"]
        if tag:
            conditions.append(self._has_tag(tag))
        rows = self.db.execute(
            select(month_key.label("month_key"), func.count(Photo.id))
            .join(MediaAsset, MediaAsset.id == Photo.asset_id)
            .where(*conditions)
            .group_by(month_key)
            .order_by(month_key.desc())
        )
        return [(str(key), int(count)) for key, count in rows if key is not None]

    def get_photo(self, photo_id: str) -> tuple[Photo, MediaAsset] | None:
        row = self.db.execute(
            select(Photo, MediaAsset)
            .join(MediaAsset, MediaAsset.id == Photo.asset_id)
            .where(
                Photo.id == photo_id,
                Photo.status == "published",
                MediaAsset.processing_status == "ready",
            )
        ).one_or_none()
        return row.tuple() if row is not None else None

    def variants_by_asset(self, asset_ids: list[str]) -> dict[str, list[MediaVariant]]:
        if not asset_ids:
            return {}
        variants: dict[str, list[MediaVariant]] = {}
        rows = self.db.scalars(
            select(MediaVariant)
            .where(MediaVariant.asset_id.in_(asset_ids))
            .order_by(MediaVariant.asset_id, MediaVariant.width)
        )
        for variant in rows:
            variants.setdefault(variant.asset_id, []).append(variant)
        return variants

    def tags_by_photo(self, photo_ids: list[str]) -> dict[str, list[str]]:
        """批量读取照片标签，避免公开列表逐条查询。"""

        result = {photo_id: [] for photo_id in photo_ids}
        if not photo_ids:
            return result
        rows = self.db.execute(
            select(PhotoTagLink.photo_id, Tag.name)
            .join(Tag, Tag.id == PhotoTagLink.tag_id)
            .where(PhotoTagLink.photo_id.in_(photo_ids))
            .order_by(PhotoTagLink.photo_id, Tag.name)
        )
        for photo_id, name in rows:
            result[photo_id].append(name)
        return result

    def public_tags(self) -> list[str]:
        """只返回至少被一张可公开照片使用的标签。"""

        usage_count = func.count(Photo.id)
        return list(self.db.scalars(
            select(Tag.name)
            .join(PhotoTagLink, PhotoTagLink.tag_id == Tag.id)
            .join(Photo, Photo.id == PhotoTagLink.photo_id)
            .join(MediaAsset, MediaAsset.id == Photo.asset_id)
            .where(Photo.status == "published", MediaAsset.processing_status == "ready")
            .group_by(Tag.id, Tag.name)
            .order_by(usage_count.desc(), Tag.name)
        ))

    @staticmethod
    def _has_tag(name: str):
        """生成按规范名称匹配标签的关联表 EXISTS 条件。"""

        return (
            select(PhotoTagLink.photo_id)
            .join(Tag, Tag.id == PhotoTagLink.tag_id)
            .where(
                PhotoTagLink.photo_id == Photo.id,
                Tag.normalized_name == " ".join(name.strip().split()).casefold(),
            )
            .exists()
        )

    def public_player_ids(self, photo_id: str) -> list[str]:
        return list(
            self.db.scalars(
                select(PhotoPlayerLink.player_id)
                .join(Player, Player.id == PhotoPlayerLink.player_id)
                .where(PhotoPlayerLink.photo_id == photo_id, Player.status != "private")
                .order_by(PhotoPlayerLink.player_id)
            )
        )

    def stories(self, photo_id: str) -> list[Story]:
        return list(
            self.db.scalars(
                select(Story)
                .join(PhotoStoryLink, PhotoStoryLink.story_id == Story.id)
                .where(PhotoStoryLink.photo_id == photo_id, Story.status == "published")
                .order_by(Story.published_at.desc(), Story.id)
            )
        )

    def list_stories(self) -> list[tuple[Story, MediaAsset]]:
        """按发布时间返回封面已经处理完成的公开作品集。"""

        rows = self.db.execute(
            select(Story, MediaAsset)
            .join(MediaAsset, MediaAsset.id == Story.cover_asset_id)
            .where(Story.status == "published", MediaAsset.processing_status == "ready")
            .order_by(Story.published_at.desc(), Story.id)
        )
        return list(rows.tuples())

    def get_story(self, story_id: str) -> Story | None:
        return self.db.scalar(
            select(Story).where(Story.id == story_id, Story.status == "published")
        )

    def ready_assets(self, asset_ids: list[str]) -> list[MediaAsset]:
        if not asset_ids:
            return []
        return list(
            self.db.scalars(
                select(MediaAsset)
                .where(
                    MediaAsset.id.in_(asset_ids),
                    MediaAsset.processing_status == "ready",
                )
                .order_by(MediaAsset.id)
            )
        )

    def public_story_player_ids(self, story_id: str) -> list[str]:
        return list(
            self.db.scalars(
                select(StoryPlayerLink.player_id)
                .join(Player, Player.id == StoryPlayerLink.player_id)
                .where(StoryPlayerLink.story_id == story_id, Player.status != "private")
                .order_by(StoryPlayerLink.player_id)
            )
        )

    def comments(self, photo_id: str) -> list[tuple[Comment, User]]:
        rows = self.db.execute(
            select(Comment, User)
            .join(User, User.id == Comment.author_user_id)
            .join(Player, Player.id == User.player_id)
            .where(
                Comment.photo_id == photo_id,
                Comment.status == "published",
                Player.status != "private",
            )
            .order_by(Comment.created_at.asc())
        )
        return list(rows.tuples())
