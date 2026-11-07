"""投稿归属、关系同步与审核状态转换规则。"""

from datetime import UTC
from typing import Any, Literal
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.security import utc_now
from app.models import (
    MediaAsset,
    Photo,
    PhotoPlayerLink,
    PhotoStoryLink,
    Player,
    Story,
    StoryPlayerLink,
)
from app.repositories.content import ContentRepository
from app.services.auth import AuthService, Principal

ContentKind = Literal["photo", "story"]
CONTENT_MODELS = {"photo": Photo, "story": Story}
CREATE_PERMISSIONS = {"photo": "photo.create", "story": "story.create"}
UPDATE_PERMISSIONS = {"photo": "photo.update.own", "story": "story.update.own"}
PUBLISH_PERMISSIONS = {"photo": "photo.publish.own", "story": "story.publish.own"}
ARCHIVE_PERMISSIONS = {"photo": "photo.archive.own", "story": "story.archive.own"}
DELETE_PERMISSIONS = {"photo": "photo.delete.any", "story": "story.delete.any"}
RELATION_FIELDS = {
    "photo": ("tags", "player_ids", "story_ids"),
    "story": ("player_ids",),
}


def new_photo_id() -> str:
    """生成不可预测且可直接用于公开网址的照片 ID。"""

    return f"photo-{uuid4().hex}"


def new_story_id() -> str:
    """生成不依赖标题的作品集稳定 ID。"""

    return f"story-{uuid4().hex}"


class ContentService:
    """普通用户只能修改自己的草稿；实体关系始终写入关联表。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ContentRepository(db)
        self.auth = AuthService(db)

    def list_for(self, kind: ContentKind, principal: Principal) -> list[dict[str, Any]]:
        model = CONTENT_MODELS[kind]
        if principal.can(DELETE_PERMISSIONS[kind]):
            items = list(self.db.scalars(select(model).order_by(model.updated_at.desc())))
        else:
            items = self.repo.list_owned(model, principal.user.id)
        return [self.serialize(kind, item) for item in items]

    def create(
        self, kind: ContentKind, principal: Principal, data: dict[str, Any]
    ) -> dict[str, Any]:
        AuthService.require(principal, CREATE_PERMISSIONS[kind])
        model = CONTENT_MODELS[kind]
        if kind == "photo":
            data["id"] = new_photo_id()
        else:
            data["id"] = new_story_id()
        if self.repo.get(model, data["id"]) is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "内容 ID 已存在")
        relations = self._pop_relations(kind, data)
        self._validate_references(principal, kind, data, relations)
        now = utc_now()
        if kind == "photo":
            data["captured_at"] = self._utc_naive(data["captured_at"])
        item = model(
            **data,
            status="draft",
            author_user_id=principal.user.id,
            published_at=None,
            published_by=None,
            rejection_reason=None,
            created_at=now,
            updated_at=now,
        )
        self.db.add(item)
        self.db.flush()
        self._replace_relations(kind, item.id, relations)
        self.db.commit()
        return self.serialize(kind, item)

    def update(
        self, kind: ContentKind, item_id: str, principal: Principal, data: dict[str, Any]
    ) -> dict[str, Any]:
        AuthService.require(principal, UPDATE_PERMISSIONS[kind])
        item = self._owned(kind, item_id, principal)
        if item.status == "deleted":
            raise HTTPException(status.HTTP_409_CONFLICT, "已删除内容不能编辑")
        relations = self._pop_relations(kind, data)
        self._validate_references(principal, kind, data, relations)
        if kind == "photo":
            data["captured_at"] = self._utc_naive(data["captured_at"])
        data.pop("id", None)
        for key, value in data.items():
            setattr(item, key, value)
        item.updated_at = utc_now()
        item.rejection_reason = None
        self._replace_relations(kind, item.id, relations)
        self.db.commit()
        return self.serialize(kind, item)

    def transition(
        self,
        kind: ContentKind,
        item_id: str,
        principal: Principal,
        target: str,
        reason: str | None,
    ) -> dict[str, Any]:
        item = self._owned(kind, item_id, principal)
        current = item.status
        if target == "published":
            AuthService.require(principal, PUBLISH_PERMISSIONS[kind])
            if current not in {"draft", "rejected", "archived"}:
                raise HTTPException(status.HTTP_409_CONFLICT, "当前状态不能发布")
            item.published_at = utc_now()
            item.published_by = principal.user.id
        elif target == "archived":
            AuthService.require(principal, ARCHIVE_PERMISSIONS[kind])
            if current != "published":
                raise HTTPException(status.HTTP_409_CONFLICT, "只有已发布内容可以归档")
        else:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "不支持的目标状态")
        item.status = target
        item.updated_at = utc_now()
        self.auth.audit(
            principal.user.id,
            f"{kind}.{target}",
            kind,
            item.id,
            {"from": current, "reason": reason} if reason else {"from": current},
        )
        self.db.commit()
        return self.serialize(kind, item)

    def delete(self, kind: ContentKind, item_id: str, principal: Principal) -> dict[str, Any]:
        """管理员软删除内容，保留关系与审计记录以便追溯。"""

        AuthService.require(principal, DELETE_PERMISSIONS[kind])
        item = self.repo.get(CONTENT_MODELS[kind], item_id)
        if item is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "内容不存在")
        if item.status == "deleted":
            raise HTTPException(status.HTTP_409_CONFLICT, "内容已经删除")
        previous = item.status
        item.status, item.updated_at = "deleted", utc_now()
        self.auth.audit(principal.user.id, f"{kind}.delete", kind, item.id, {"from": previous})
        self.db.commit()
        return self.serialize(kind, item)

    def serialize(self, kind: ContentKind, item: Any) -> dict[str, Any]:
        common = {
            "status": item.status,
            "author_user_id": item.author_user_id,
            "rejection_reason": item.rejection_reason,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }
        if kind == "photo":
            return {
                **common,
                "id": item.id,
                "title": item.title,
                "description": item.description,
                "asset_id": item.asset_id,
                "captured_at": item.captured_at,
                "photographer_id": item.photographer_id,
                "tags": self.repo.tag_names(item.id),
                "player_ids": self._ids(PhotoPlayerLink, "photo_id", "player_id", item.id),
                "story_ids": self._ids(PhotoStoryLink, "photo_id", "story_id", item.id),
                "featured": item.featured,
                "display_variant": item.display_variant,
            }
        if kind == "story":
            return {
                **common,
                "id": item.id,
                "title": item.title,
                "summary": item.summary,
                "cover_asset_id": item.cover_asset_id,
                "sections": item.sections,
                "player_ids": self._ids(StoryPlayerLink, "story_id", "player_id", item.id),
            }
        raise ValueError(f"不支持的内容类型：{kind}")

    def _ids(
        self, link_model: type[Any], parent_name: str, value_name: str, item_id: str
    ) -> list[str]:
        parent = getattr(link_model, parent_name)
        value = getattr(link_model, value_name)
        return list(self.db.scalars(select(value).where(parent == item_id).order_by(value)))

    @staticmethod
    def _pop_relations(kind: ContentKind, data: dict[str, Any]) -> dict[str, list[str]]:
        return {field: data.pop(field, []) for field in RELATION_FIELDS[kind]}

    def _replace_relations(
        self, kind: ContentKind, item_id: str, relations: dict[str, list[str]]
    ) -> None:
        configurations: dict[str, dict[str, tuple[type[Any], str, str]]] = {
            "photo": {
                "player_ids": (PhotoPlayerLink, "photo_id", "player_id"),
                "story_ids": (PhotoStoryLink, "photo_id", "story_id"),
            },
            "story": {
                "player_ids": (StoryPlayerLink, "story_id", "player_id"),
            },
        }
        for field, values in relations.items():
            if kind == "photo" and field == "tags":
                self.repo.replace_photo_tags(item_id, values, utc_now())
                continue
            link_model, parent_name, value_name = configurations[kind][field]
            parent_column = getattr(link_model, parent_name)
            self.db.execute(delete(link_model).where(parent_column == item_id))
            for value in dict.fromkeys(values):
                self.db.add(link_model(**{parent_name: item_id, value_name: value}))

    def _validate_references(
        self,
        principal: Principal,
        kind: ContentKind,
        data: dict[str, Any],
        relations: dict[str, list[str]],
    ) -> None:
        self._validate_media(principal, kind, data)
        reference_models = {
            "player_ids": Player,
            "story_ids": Story,
        }
        for field, values in relations.items():
            if field == "tags":
                continue
            model = reference_models[field]
            missing = [value for value in values if self.db.get(model, value) is None]
            if missing:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    f"关联对象不存在：{', '.join(missing)}",
                )

    def _owned(self, kind: ContentKind, item_id: str, principal: Principal) -> Any:
        item = self.repo.get(CONTENT_MODELS[kind], item_id)
        if item is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "内容不存在")
        if item.author_user_id != principal.user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "只能操作自己的内容")
        return item

    def _validate_media(
        self, principal: Principal, kind: ContentKind, data: dict[str, Any]
    ) -> None:
        asset_ids: list[str] = []
        if kind == "photo":
            asset_ids.append(data["asset_id"])
        elif kind == "story":
            asset_ids.append(data["cover_asset_id"])
            for section in data["sections"]:
                if section.get("assetId"):
                    asset_ids.append(section["assetId"])
                asset_ids.extend(section.get("assetIds", []))
        for asset_id in set(asset_ids):
            asset = self.db.get(MediaAsset, asset_id)
            if asset is None or asset.processing_status != "ready":
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"媒体不可用：{asset_id}")
            if asset.owner_user_id != principal.user.id:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "不能使用其他用户的未发布媒体")

    @staticmethod
    def _utc_naive(value: Any) -> Any:
        if value.tzinfo is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "时间必须包含时区")
        return value.astimezone(UTC).replace(tzinfo=None)
