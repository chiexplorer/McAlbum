"""检查数据库媒体元数据与本地持久化文件的一致性。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import utc_now
from app.models import MediaAsset, MediaVariant, Photo, Player, Story
from app.services.auth import AuthService


@dataclass(slots=True)
class InvalidMedia:
    """一个文件不完整的媒体资产及其原因。"""

    asset_id: str
    reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MediaIntegrityReport:
    """媒体扫描结果及会被清理的业务实体 ID。"""

    invalid_media: list[InvalidMedia]
    photo_ids: list[str]
    story_ids: list[str]
    player_ids: list[str]

    @property
    def has_issues(self) -> bool:
        return bool(self.invalid_media)


class MediaIntegrityService:
    """扫描缺失原图或变体，并以可恢复状态变更隔离受影响内容。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.media_root = get_settings().media_root.resolve()

    def scan(self) -> MediaIntegrityReport:
        """只读扫描媒体文件，并计算直接引用无效媒体的内容。"""

        invalid_media = self._invalid_media()
        invalid_ids = {item.asset_id for item in invalid_media}
        if not invalid_ids:
            return MediaIntegrityReport([], [], [], [])

        photos = self.db.scalars(
            select(Photo).where(Photo.asset_id.in_(invalid_ids), Photo.status != "deleted")
        )
        stories = self.db.scalars(select(Story).where(Story.status != "deleted"))
        players = self.db.scalars(
            select(Player).where(Player.avatar_asset_id.in_(invalid_ids))
        )
        return MediaIntegrityReport(
            invalid_media=invalid_media,
            photo_ids=sorted(item.id for item in photos),
            story_ids=sorted(
                item.id for item in stories if self._story_asset_ids(item) & invalid_ids
            ),
            player_ids=sorted(item.id for item in players),
        )

    def apply(self, report: MediaIntegrityReport, actor_user_id: str) -> None:
        """应用可恢复清理：媒体标记失败，内容软删除，玩家头像解绑。"""

        now = utc_now()
        auth = AuthService(self.db)
        invalid_ids = {item.asset_id for item in report.invalid_media}
        for asset in self.db.scalars(select(MediaAsset).where(MediaAsset.id.in_(invalid_ids))):
            asset.processing_status = "failed"
            asset.updated_at = now

        for photo in self.db.scalars(select(Photo).where(Photo.id.in_(report.photo_ids))):
            previous = photo.status
            photo.status = "deleted"
            photo.updated_at = now
            auth.audit(
                actor_user_id, "photo.delete.missing_media", "photo", photo.id,
                {"from": previous, "assetId": photo.asset_id},
            )

        for story in self.db.scalars(select(Story).where(Story.id.in_(report.story_ids))):
            previous = story.status
            story.status = "deleted"
            story.updated_at = now
            auth.audit(
                actor_user_id, "story.delete.missing_media", "story", story.id,
                {"from": previous},
            )

        for player in self.db.scalars(select(Player).where(Player.id.in_(report.player_ids))):
            player.avatar_asset_id = None
            player.updated_at = now
            auth.audit(
                actor_user_id, "profile.avatar.detach_missing_media", "player", player.id
            )

    def _invalid_media(self) -> list[InvalidMedia]:
        referenced_ids = set(
            self.db.scalars(select(Photo.asset_id).where(Photo.status != "deleted"))
        )
        for story in self.db.scalars(select(Story).where(Story.status != "deleted")):
            referenced_ids.update(self._story_asset_ids(story))
        referenced_ids.update(
            item for item in self.db.scalars(select(Player.avatar_asset_id)) if item
        )
        variants_by_asset: dict[str, list[MediaVariant]] = {}
        for variant in self.db.scalars(select(MediaVariant)):
            variants_by_asset.setdefault(variant.asset_id, []).append(variant)

        result: list[InvalidMedia] = []
        for asset in self.db.scalars(select(MediaAsset).order_by(MediaAsset.id)):
            reasons: list[str] = []
            if asset.processing_status != "ready":
                if asset.id in referenced_ids:
                    reasons.append(f"处理状态不是 ready：{asset.processing_status}")
            else:
                self._check_file(asset.storage_key, "原图", reasons)
                variants = variants_by_asset.get(asset.id, [])
                if not variants:
                    reasons.append("缺少媒体变体记录")
                for variant in variants:
                    self._check_file(variant.storage_key, f"变体 {variant.name}", reasons)
            if reasons:
                result.append(InvalidMedia(asset.id, reasons))
        return result

    def _check_file(self, storage_key: str | None, label: str, reasons: list[str]) -> None:
        if not storage_key:
            reasons.append(f"{label}缺少 storage key")
            return
        candidate = (self.media_root / storage_key).resolve()
        if self.media_root not in candidate.parents or not candidate.is_file():
            reasons.append(f"{label}文件不存在：{storage_key}")

    @classmethod
    def _story_asset_ids(cls, story: Story) -> set[str]:
        asset_ids = {story.cover_asset_id}
        cls._collect_section_assets(story.sections, asset_ids)
        return asset_ids

    @classmethod
    def _collect_section_assets(cls, value: Any, asset_ids: set[str]) -> None:
        if isinstance(value, dict):
            asset_id = value.get("assetId")
            if isinstance(asset_id, str):
                asset_ids.add(asset_id)
            group = value.get("assetIds")
            if isinstance(group, list):
                asset_ids.update(item for item in group if isinstance(item, str))
            for nested in value.values():
                cls._collect_section_assets(nested, asset_ids)
        elif isinstance(value, list):
            for nested in value:
                cls._collect_section_assets(nested, asset_ids)
