"""已登录玩家评论与管理员审核接口。"""

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.dependencies import CsrfPrincipal, Db, PrincipalDep
from app.core.rate_limit import limit
from app.core.security import utc_now
from app.models import Comment, Photo
from app.schemas.content import CommentCreate, CommentModeration, CommentResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/comments")
comment_limit = limit("comment", 12, 300)
CommentLimited = Annotated[None, Depends(comment_limit)]


@router.get("/photo/{photo_id}", response_model=list[CommentResponse])
def list_comments(photo_id: str, principal: PrincipalDep, db: Db) -> list[Comment]:
    query = select(Comment).where(Comment.photo_id == photo_id)
    if not principal.can("comment.moderate"):
        query = query.where(Comment.status == "published")
    return list(db.scalars(query.order_by(Comment.created_at.asc())))


@router.post(
    "/photo/{photo_id}", response_model=CommentResponse, status_code=status.HTTP_201_CREATED
)
def create_comment(
    photo_id: str,
    payload: CommentCreate,
    principal: CsrfPrincipal,
    db: Db,
    _limited: CommentLimited,
) -> Comment:
    AuthService.require(principal, "comment.create")
    photo = db.get(Photo, photo_id)
    if photo is None or photo.status != "published":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "照片不存在或尚未发布")
    now = utc_now()
    comment = Comment(
        id=f"cmt_{uuid4().hex}",
        photo_id=photo_id,
        author_user_id=principal.user.id,
        body=payload.body,
        status="published",
        hidden_reason=None,
        created_at=now,
        updated_at=now,
    )
    db.add(comment)
    db.commit()
    return comment


@router.post("/{comment_id}/moderate", response_model=CommentResponse)
def moderate_comment(
    comment_id: str,
    payload: CommentModeration,
    principal: CsrfPrincipal,
    db: Db,
) -> Comment:
    AuthService.require(principal, "comment.moderate")
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "评论不存在")
    comment.status = "hidden" if payload.hidden else "published"
    comment.hidden_reason = payload.reason if payload.hidden else None
    comment.updated_at = utc_now()
    AuthService(db).audit(
        principal.user.id,
        "comment.hide" if payload.hidden else "comment.restore",
        "comment",
        comment.id,
        {"reason": payload.reason} if payload.reason else {},
    )
    db.commit()
    return comment
