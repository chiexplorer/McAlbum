"""照片和作品集的草稿与审核接口。"""

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CsrfPrincipal, Db, PrincipalDep
from app.schemas.content import (
    PhotoResponse,
    PhotoWrite,
    StoryResponse,
    StoryWrite,
    TagResponse,
    TransitionRequest,
)
from app.services.content import ContentService
from app.services.tags import TagService

router = APIRouter(prefix="/manage")


@router.get("/tags", response_model=list[TagResponse])
def list_tags(principal: PrincipalDep, db: Db) -> list[object]:
    """为照片编目提供受控的标签候选目录。"""

    allowed = {"photo.create", "photo.update.own", "tag.manage"}
    if not allowed.intersection(principal.permissions):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "缺少照片编目权限")
    return TagService(db).list_catalog()


@router.get("/photos", response_model=list[PhotoResponse])
def list_photos(principal: PrincipalDep, db: Db) -> list[object]:
    return ContentService(db).list_for("photo", principal)


@router.post("/photos", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED)
def create_photo(payload: PhotoWrite, principal: CsrfPrincipal, db: Db) -> object:
    return ContentService(db).create("photo", principal, payload.model_dump())


@router.put("/photos/{item_id}", response_model=PhotoResponse)
def update_photo(item_id: str, payload: PhotoWrite, principal: CsrfPrincipal, db: Db) -> object:
    return ContentService(db).update("photo", item_id, principal, payload.model_dump())


@router.post("/photos/{item_id}/transition", response_model=PhotoResponse)
def transition_photo(
    item_id: str,
    payload: TransitionRequest,
    principal: CsrfPrincipal,
    db: Db,
) -> object:
    return ContentService(db).transition(
        "photo", item_id, principal, payload.target_status, payload.reason
    )


@router.delete("/photos/{item_id}", response_model=PhotoResponse)
def delete_photo(item_id: str, principal: CsrfPrincipal, db: Db) -> object:
    return ContentService(db).delete("photo", item_id, principal)


@router.get("/stories", response_model=list[StoryResponse])
def list_stories(principal: PrincipalDep, db: Db) -> list[object]:
    return ContentService(db).list_for("story", principal)


@router.post("/stories", response_model=StoryResponse, status_code=status.HTTP_201_CREATED)
def create_story(payload: StoryWrite, principal: CsrfPrincipal, db: Db) -> object:
    return ContentService(db).create("story", principal, payload.model_dump())


@router.put("/stories/{item_id}", response_model=StoryResponse)
def update_story(item_id: str, payload: StoryWrite, principal: CsrfPrincipal, db: Db) -> object:
    return ContentService(db).update("story", item_id, principal, payload.model_dump())


@router.post("/stories/{item_id}/transition", response_model=StoryResponse)
def transition_story(
    item_id: str,
    payload: TransitionRequest,
    principal: CsrfPrincipal,
    db: Db,
) -> object:
    return ContentService(db).transition(
        "story", item_id, principal, payload.target_status, payload.reason
    )


@router.delete("/stories/{item_id}", response_model=StoryResponse)
def delete_story(item_id: str, principal: CsrfPrincipal, db: Db) -> object:
    return ContentService(db).delete("story", item_id, principal)
