"""标签目录的查询与管理员维护规则。"""

from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import utc_now
from app.models import Tag
from app.repositories.content import ContentRepository
from app.services.auth import AuthService, Principal


class TagService:
    """集中维护稳定标签 ID、名称唯一性和管理审计。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ContentRepository(db)
        self.auth = AuthService(db)

    def list_catalog(self) -> list[dict[str, object]]:
        return [
            {"id": tag.id, "name": tag.name, "usage_count": count,
             "created_at": tag.created_at}
            for tag, count in self.repo.list_tags()
        ]

    def create(self, principal: Principal, name: str) -> dict[str, object]:
        AuthService.require(principal, "tag.manage")
        normalized = name.casefold()
        if self.repo.tag_by_normalized_name(normalized) is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "标签名称已存在")
        tag = Tag(id=f"tag-{uuid4().hex}", name=name,
                  normalized_name=normalized, created_at=utc_now())
        self.db.add(tag)
        self.auth.audit(principal.user.id, "tag.create", "tag", tag.id, {"name": name})
        self.db.commit()
        return self._response(tag, 0)

    def update(self, principal: Principal, tag_id: str, name: str) -> dict[str, object]:
        AuthService.require(principal, "tag.manage")
        tag = self._get(tag_id)
        normalized = name.casefold()
        duplicate = self.repo.tag_by_normalized_name(normalized)
        if duplicate is not None and duplicate.id != tag.id:
            raise HTTPException(status.HTTP_409_CONFLICT, "标签名称已存在")
        previous = tag.name
        tag.name, tag.normalized_name = name, normalized
        self.auth.audit(principal.user.id, "tag.update", "tag", tag.id,
                        {"from": previous, "to": name})
        self.db.commit()
        usage_count = next(
            (count for item, count in self.repo.list_tags() if item.id == tag.id), 0
        )
        return self._response(tag, usage_count)

    def delete(self, principal: Principal, tag_id: str) -> None:
        AuthService.require(principal, "tag.manage")
        tag = self._get(tag_id)
        usage_count = next(
            (count for item, count in self.repo.list_tags() if item.id == tag.id), 0
        )
        self.auth.audit(principal.user.id, "tag.delete", "tag", tag.id,
                        {"name": tag.name, "usage_count": usage_count})
        self.db.delete(tag)
        self.db.commit()

    def _get(self, tag_id: str) -> Tag:
        tag = self.db.get(Tag, tag_id)
        if tag is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "标签不存在")
        return tag

    @staticmethod
    def _response(tag: Tag, usage_count: int) -> dict[str, object]:
        return {"id": tag.id, "name": tag.name, "usage_count": usage_count,
                "created_at": tag.created_at}
