"""玩家资料、媒体和投稿内容 API 契约。"""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PublicationStatus = Literal["draft", "pending", "published", "rejected", "archived", "deleted"]


class PlayerProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    bio: str = Field(max_length=4000)
    status: Literal["resident", "historical", "private"]
    joined_at: date | None = None
    avatar_asset_id: str | None = None


class PlayerProfile(PlayerProfileUpdate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    work_ids: list[str]


class MediaVariantResponse(BaseModel):
    name: str
    url: str
    width: int
    height: int


class MediaAssetResponse(BaseModel):
    id: str
    alt_text: str
    captured_at: datetime
    focal_x: float
    focal_y: float
    width: int
    height: int
    processing_status: str
    editorial_status: str
    variants: list[MediaVariantResponse]


class PhotoWrite(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=10000)
    asset_id: str
    captured_at: datetime
    photographer_id: str | None = None
    tags: list[str] = Field(default_factory=list, max_length=30)
    player_ids: list[str] = Field(default_factory=list)
    story_ids: list[str] = Field(default_factory=list)
    featured: bool = False
    display_variant: Literal["featured", "normal", "portrait", "note"] = "normal"

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        """清理空标签，并按不区分大小写的名称去重。"""

        result: list[str] = []
        seen: set[str] = set()
        for item in value:
            name = " ".join(item.strip().split())
            normalized = name.casefold()
            if not name or normalized in seen:
                continue
            if len(name) > 64:
                raise ValueError("单个标签不能超过 64 个字符")
            seen.add(normalized)
            result.append(name)
        return result


class PhotoResponse(PhotoWrite):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: PublicationStatus
    author_user_id: str
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime


class StoryWrite(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    summary: str = Field(min_length=1, max_length=10000)
    cover_asset_id: str
    sections: list[dict[str, Any]] = Field(min_length=1)
    player_ids: list[str] = Field(default_factory=list)

    @field_validator("sections")
    @classmethod
    def section_ids_are_unique(cls, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        from uuid import uuid4

        value = [
            {**section, "id": section.get("id") or f"section-{uuid4().hex}"}
            for section in value
        ]
        ids = [section.get("id") for section in value]
        if None in ids or len(ids) != len(set(ids)):
            raise ValueError("每个区块必须有唯一 id")
        return value


class StoryResponse(StoryWrite):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: PublicationStatus
    author_user_id: str
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime


class TransitionRequest(BaseModel):
    target_status: Literal["published", "archived"]
    reason: str | None = Field(default=None, max_length=500)


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=1000)


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    photo_id: str
    author_user_id: str
    body: str
    status: Literal["published", "withdrawn", "deleted"]
    deletion_reason: str | None
    deleted_at: datetime | None
    created_at: datetime


class CommentDelete(BaseModel):
    reason: str | None = Field(default=None, max_length=500)
