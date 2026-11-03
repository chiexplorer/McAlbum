"""当前用户的玩家档案接口。"""

from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import CsrfPrincipal, Db, PrincipalDep
from app.core.security import utc_now
from app.models import MediaAsset, Player, StoryPlayerLink
from app.repositories.content import ContentRepository
from app.schemas.content import PlayerProfile, PlayerProfileUpdate
from app.services.auth import AuthService

router = APIRouter(prefix="/manage/profile")


def profile_response(db: Session, player: Player) -> dict[str, object]:
    """把规范化关联表投影为玩家档案 API 字段。"""

    return {
        "id": player.id,
        "name": player.name,
        "bio": player.bio,
        "status": player.status,
        "avatar_asset_id": player.avatar_asset_id,
        "joined_at": player.joined_at,
        "work_ids": list(
            db.scalars(
                select(StoryPlayerLink.story_id).where(StoryPlayerLink.player_id == player.id)
            )
        ),
    }


@router.get("", response_model=PlayerProfile)
def get_profile(principal: PrincipalDep, db: Db) -> dict[str, object]:
    player = ContentRepository(db).player_for_user(principal.user.player_id)
    if player is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "尚未建立玩家档案")
    return profile_response(db, player)


@router.put("", response_model=PlayerProfile)
def update_profile(
    payload: PlayerProfileUpdate,
    principal: CsrfPrincipal,
    db: Db,
) -> dict[str, object]:
    AuthService.require(principal, "profile.self.update")
    if payload.avatar_asset_id:
        asset = db.get(MediaAsset, payload.avatar_asset_id)
        if asset is None or (not principal.is_admin and asset.owner_user_id != principal.user.id):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "头像媒体不可用")
    now = utc_now()
    player = ContentRepository(db).player_for_user(principal.user.player_id)
    if player is None:
        player = Player(
            id=f"player-{uuid4().hex[:16]}",
            created_at=now,
            updated_at=now,
            **payload.model_dump(),
        )
        db.add(player)
        db.flush()
        principal.user.player_id = player.id
    else:
        for key, value in payload.model_dump().items():
            setattr(player, key, value)
        player.updated_at = now
    principal.user.updated_at = now
    db.commit()
    return profile_response(db, player)
