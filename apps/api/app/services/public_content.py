"""把已发布数据库内容投影为浏览器安全的公开模型。"""

from datetime import UTC, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import MediaAsset, MediaVariant, Photo, Story
from app.repositories.public_content import PublicContentRepository
from app.schemas.public_content import (
    PublicComment,
    PublicFocalPoint,
    PublicMediaAsset,
    PublicMediaVariant,
    PublicPhoto,
    PublicPhotoCursor,
    PublicPhotoDetail,
    PublicPhotoEntry,
    PublicPhotoFeed,
    PublicPhotoMonth,
    PublicStory,
    PublicStoryDetail,
    PublicStoryEntry,
)

BEIJING = timezone(timedelta(hours=8), "Asia/Shanghai")


def beijing_iso(value: datetime) -> str:
    """数据库无时区时间按 UTC 解释，并输出北京时区 ISO 字符串。"""

    return value.replace(tzinfo=UTC).astimezone(BEIJING).isoformat(timespec="seconds")


class PublicContentService:
    """公开读取服务；所有状态和隐私过滤均在服务端完成。"""

    def __init__(self, db: Session) -> None:
        self.repo = PublicContentRepository(db)

    def list_photos(self) -> list[PublicPhotoEntry]:
        rows = self.repo.list_photos()
        variants = self.repo.variants_by_asset([asset.id for _, asset in rows])
        tags = self.repo.tags_by_photo([photo.id for photo, _ in rows])
        return [
            PublicPhotoEntry(
                photo=self._photo(photo, tags=tags.get(photo.id, [])),
                asset=self._asset(asset, variants.get(asset.id, [])),
            )
            for photo, asset in rows
            if variants.get(asset.id)
        ]

    def list_photo_feed(
        self,
        *,
        limit: int,
        before: datetime | None = None,
        before_id: str | None = None,
        month: str | None = None,
        tag: str | None = None,
    ) -> PublicPhotoFeed:
        """按拍摄时间返回一页照片，并生成稳定的下一页游标。"""

        before_utc = self._utc_naive(before) if before is not None else None
        month_start, month_end = self._month_bounds(month)
        rows, has_more = self.repo.list_photo_feed(
            limit=limit,
            before=before_utc,
            before_id=before_id,
            month_start=month_start,
            month_end=month_end,
            tag=tag,
        )
        variants = self.repo.variants_by_asset([asset.id for _, asset in rows])
        tags = self.repo.tags_by_photo([photo.id for photo, _ in rows])
        items = [
            PublicPhotoEntry(
                photo=self._photo(photo, tags=tags.get(photo.id, [])),
                asset=self._asset(asset, variants.get(asset.id, [])),
            )
            for photo, asset in rows
            if variants.get(asset.id)
        ]
        last_photo = rows[-1][0] if rows and has_more else None
        next_cursor = (
            PublicPhotoCursor(captured_at=beijing_iso(last_photo.captured_at), id=last_photo.id)
            if last_photo is not None
            else None
        )
        return PublicPhotoFeed(items=items, next_cursor=next_cursor, has_more=has_more)

    def photo_timeline(self, tag: str | None = None) -> list[PublicPhotoMonth]:
        """返回按北京时间月份倒序排列的照片数量索引。"""

        return [
            PublicPhotoMonth(
                key=key,
                year=int(key[:4]),
                month=int(key[5:7]),
                count=count,
            )
            for key, count in self.repo.photo_timeline(tag)
        ]

    def get_photo(self, photo_id: str) -> PublicPhotoDetail | None:
        row = self.repo.get_photo(photo_id)
        if row is None:
            return None
        photo, asset = row
        main_variants = self.repo.variants_by_asset([asset.id]).get(asset.id, [])
        if not main_variants:
            return None
        candidate_rows = self.repo.list_photos()
        tags = self.repo.tags_by_photo([item[0].id for item in candidate_rows])
        photo_tags = set(tags.get(photo.id, []))
        related_rows = [
            item
            for item in candidate_rows
            if item[0].id != photo.id
            and bool(set(tags.get(item[0].id, [])) & photo_tags)
        ][:3]
        assets = [asset, *(item[1] for item in related_rows)]
        variants = self.repo.variants_by_asset([item.id for item in assets])
        stories = self.repo.stories(photo.id)
        player_ids = self.repo.public_player_ids(photo.id)
        comments = [
            PublicComment(
                id=comment.id.replace("_", "-")[:100],
                author_player_id=user.player_id,
                body=comment.body,
                created_at=beijing_iso(comment.created_at),
            )
            for comment, user in self.repo.comments(photo.id)
            if user.player_id is not None
        ]
        return PublicPhotoDetail(
            photo=self._photo(
                photo,
                tags=tags.get(photo.id, []),
                player_ids=player_ids,
                story_ids=[item.id for item in stories],
                comments=comments,
            ),
            asset=self._asset(asset, variants.get(asset.id, [])),
            stories=[self._story(item) for item in stories],
            related_photos=[
                PublicPhotoEntry(
                    photo=self._photo(item_photo, tags=tags.get(item_photo.id, [])),
                    asset=self._asset(item_asset, variants.get(item_asset.id, [])),
                )
                for item_photo, item_asset in related_rows
            ],
        )

    def list_stories(self) -> list[PublicStoryEntry]:
        rows = self.repo.list_stories()
        variants = self.repo.variants_by_asset([asset.id for _, asset in rows])
        return [
            PublicStoryEntry(
                story=self._story(story),
                cover_asset=self._asset(asset, variants.get(asset.id, [])),
            )
            for story, asset in rows
            if variants.get(asset.id)
        ]

    def get_story(self, story_id: str) -> PublicStoryDetail | None:
        story = self.repo.get_story(story_id)
        if story is None:
            return None
        asset_ids = self._story_asset_ids(story)
        assets = self.repo.ready_assets(asset_ids)
        if {asset.id for asset in assets} != set(asset_ids):
            return None
        variants = self.repo.variants_by_asset(asset_ids)
        if any(not variants.get(asset.id) for asset in assets):
            return None
        return PublicStoryDetail(
            story=self._story(story),
            assets=[self._asset(asset, variants[asset.id]) for asset in assets],
        )

    def _photo(
        self,
        photo: Photo,
        *,
        tags: list[str],
        player_ids: list[str] | None = None,
        story_ids: list[str] | None = None,
        comments: list[PublicComment] | None = None,
    ) -> PublicPhoto:
        return PublicPhoto(
            id=photo.id,
            title=photo.title,
            description=photo.description,
            asset_id=photo.asset_id,
            captured_at=beijing_iso(photo.captured_at),
            # 摄影者公开状态尚未确认时不暴露玩家 ID。
            photographer_id=None,
            player_ids=player_ids or [],
            story_ids=story_ids or [],
            tags=tags,
            featured=photo.featured,
            display_variant=photo.display_variant,
            comments=comments or [],
        )

    @staticmethod
    def _asset(asset: MediaAsset, variants: list[MediaVariant]) -> PublicMediaAsset:
        return PublicMediaAsset(
            id=asset.id,
            alt_text=asset.alt_text,
            focal_point=PublicFocalPoint(x=float(asset.focal_x), y=float(asset.focal_y)),
            variants=[
                PublicMediaVariant(
                    name=item.name,
                    storage_key=item.storage_key,
                    mime_type="image/webp",
                    byte_size=item.byte_size,
                    width=item.width,
                    height=item.height,
                    sha256=item.sha256,
                )
                for item in variants
            ],
        )

    def _story(self, story: Story) -> PublicStory:
        player_ids = self.repo.public_story_player_ids(story.id)
        sections = [
            section
            for section in story.sections
            if section.get("type") != "player-quote"
            or section.get("playerId") in player_ids
        ]
        return PublicStory(
            id=story.id,
            title=story.title,
            summary=story.summary,
            cover_asset_id=story.cover_asset_id,
            player_ids=player_ids,
            sections=sections,
        )

    @staticmethod
    def _story_asset_ids(story: Story) -> list[str]:
        """提取作品集实际需要公开的媒体，避免读取任意 JSON 字段。"""

        asset_ids = [story.cover_asset_id]
        for section in story.sections:
            if section.get("type") in {"wide-image", "text-with-image"}:
                asset_id = section.get("assetId")
                if isinstance(asset_id, str):
                    asset_ids.append(asset_id)
            elif section.get("type") == "image-grid":
                asset_ids.extend(
                    item for item in section.get("assetIds", []) if isinstance(item, str)
                )
        return list(dict.fromkeys(asset_ids))

    @staticmethod
    def _utc_naive(value: datetime) -> datetime:
        """把带时区的公开游标转换为数据库使用的无时区 UTC。"""

        if value.tzinfo is None:
            raise ValueError("游标时间必须包含时区")
        return value.astimezone(UTC).replace(tzinfo=None)

    @staticmethod
    def _month_bounds(month: str | None) -> tuple[datetime | None, datetime | None]:
        """把 YYYY-MM 北京月份转换成左闭右开的 UTC 查询边界。"""

        if month is None:
            return None, None
        year, month_number = (int(part) for part in month.split("-"))
        start = datetime(year, month_number, 1, tzinfo=BEIJING)
        if month_number == 12:
            end = datetime(year + 1, 1, 1, tzinfo=BEIJING)
        else:
            end = datetime(year, month_number + 1, 1, tzinfo=BEIJING)
        return (
            start.astimezone(UTC).replace(tzinfo=None),
            end.astimezone(UTC).replace(tzinfo=None),
        )
