"""协作内容数据库访问。"""

import hashlib
from datetime import datetime
from typing import TypeVar

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models import Comment, MediaAsset, Photo, PhotoTagLink, Player, Story, Tag

ContentModel = Photo | Story
ModelT = TypeVar("ModelT", bound=Base)


class ContentRepository:
    """为 Service 层提供清晰且可替换的内容持久化边界。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, model: type[ModelT], item_id: str) -> ModelT | None:
        return self.db.get(model, item_id)

    def list_owned(self, model: type[ModelT], user_id: str) -> list[ModelT]:
        return list(
            self.db.scalars(
                select(model)
                .where(model.author_user_id == user_id)  # type: ignore[attr-defined]
                .order_by(model.updated_at.desc())  # type: ignore[attr-defined]
            )
        )

    def list_pending(self, model: type[ModelT]) -> list[ModelT]:
        return list(
            self.db.scalars(
                select(model)
                .where(model.status == "pending")  # type: ignore[attr-defined]
                .order_by(model.updated_at.asc())  # type: ignore[attr-defined]
            )
        )

    def list_media(self, user_id: str | None = None) -> list[MediaAsset]:
        query = select(MediaAsset).order_by(MediaAsset.created_at.desc())
        if user_id is not None:
            query = query.where(MediaAsset.owner_user_id == user_id)
        return list(self.db.scalars(query))

    def comments_for_photo(self, photo_id: str) -> list[Comment]:
        return list(
            self.db.scalars(
                select(Comment)
                .where(Comment.photo_id == photo_id)
                .order_by(Comment.created_at.asc())
            )
        )

    def player_for_user(self, player_id: str | None) -> Player | None:
        return self.db.get(Player, player_id) if player_id else None

    def tag_names(self, photo_id: str) -> list[str]:
        """按稳定顺序返回照片关联的标签显示名称。"""

        return list(
            self.db.scalars(
                select(Tag.name)
                .join(PhotoTagLink, PhotoTagLink.tag_id == Tag.id)
                .where(PhotoTagLink.photo_id == photo_id)
                .order_by(Tag.name)
            )
        )

    def replace_photo_tags(
        self, photo_id: str, names: list[str], created_at: datetime
    ) -> None:
        """复用或创建标签，并原子替换指定照片的标签关系。"""

        cleaned_names = [" ".join(name.strip().split()) for name in names]
        normalized_names = {name.casefold(): name for name in cleaned_names if name}
        existing = {
            tag.normalized_name: tag
            for tag in self.db.scalars(
                select(Tag).where(Tag.normalized_name.in_(normalized_names))
            )
        }
        self.db.execute(delete(PhotoTagLink).where(PhotoTagLink.photo_id == photo_id))
        for normalized_name, name in normalized_names.items():
            tag = existing.get(normalized_name)
            if tag is None:
                digest = hashlib.sha256(normalized_name.encode("utf-8")).hexdigest()[:32]
                tag = Tag(
                    id=f"tag-{digest}",
                    name=name,
                    normalized_name=normalized_name,
                    created_at=created_at,
                )
                self.db.add(tag)
                self.db.flush()
            self.db.add(PhotoTagLink(photo_id=photo_id, tag_id=tag.id))
