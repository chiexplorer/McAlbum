"""面向匿名访客的公开内容契约。"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class PublicModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class PublicMediaVariant(PublicModel):
    name: str
    storage_key: str
    mime_type: Literal["image/webp"]
    byte_size: int
    width: int
    height: int
    sha256: str


class PublicFocalPoint(PublicModel):
    x: float
    y: float


class PublicMediaAsset(PublicModel):
    id: str
    alt_text: str
    focal_point: PublicFocalPoint
    original_url: str
    variants: list[PublicMediaVariant] = Field(min_length=1)


class PublicComment(PublicModel):
    id: str
    author_player_id: str
    body: str
    status: Literal["published"] = "published"
    created_at: str


class PublicPhoto(PublicModel):
    id: str
    title: str
    description: str
    asset_id: str
    captured_at: str
    time_zone: Literal["Asia/Shanghai"] = "Asia/Shanghai"
    photographer_id: str | None = None
    player_ids: list[str] = Field(default_factory=list)
    story_ids: list[str] = Field(default_factory=list)
    tags: list[str]
    status: Literal["published"] = "published"
    is_mock: Literal[False] = False
    featured: bool
    display_variant: Literal["featured", "normal", "portrait", "note"]
    comments: list[PublicComment] = Field(default_factory=list)


class PublicStory(PublicModel):
    id: str
    title: str
    summary: str
    cover_asset_id: str
    player_ids: list[str] = Field(default_factory=list)
    sections: list[dict[str, Any]]
    status: Literal["published"] = "published"
    is_mock: Literal[False] = False


class PublicPhotoEntry(PublicModel):
    photo: PublicPhoto
    asset: PublicMediaAsset


class PublicPhotoCursor(PublicModel):
    """下一页的拍摄时间与稳定 ID 游标。"""

    captured_at: str
    id: str


class PublicPhotoFeed(PublicModel):
    """按拍摄时间倒序返回的一页公开照片。"""

    items: list[PublicPhotoEntry]
    next_cursor: PublicPhotoCursor | None = None
    has_more: bool


class PublicPhotoMonth(PublicModel):
    """按北京时间归档的单个月份及公开照片数量。"""

    key: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    year: int
    month: int = Field(ge=1, le=12)
    count: int = Field(ge=1)


class PublicPhotoDetail(PublicPhotoEntry):
    stories: list[PublicStory] = Field(default_factory=list)
    related_photos: list[PublicPhotoEntry] = Field(default_factory=list)


class PublicStoryEntry(PublicModel):
    story: PublicStory
    cover_asset: PublicMediaAsset


class PublicStoryDetail(PublicModel):
    story: PublicStory
    assets: list[PublicMediaAsset] = Field(min_length=1)
