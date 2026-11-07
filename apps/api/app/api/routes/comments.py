"""已登录玩家的评论发布、本人撤回和管理员软删除接口。"""

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.dependencies import CsrfPrincipal, Db, PrincipalDep
from app.core.rate_limit import limit
from app.core.security import utc_now
from app.models import Comment, Photo
from app.schemas.content import CommentCreate, CommentDelete, CommentResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/comments")
CommentLimited = Annotated[None, Depends(limit("comment", 12, 300))]


@router.get("/photo/{photo_id}", response_model=list[CommentResponse])
def list_comments(photo_id: str, principal: PrincipalDep, db: Db) -> list[Comment]:
    query = select(Comment).where(Comment.photo_id == photo_id)
    if not principal.can("comment.delete.any"):
        query = query.where(Comment.status == "published")
    return list(db.scalars(query.order_by(Comment.created_at.asc())))


@router.post("/photo/{photo_id}", response_model=CommentResponse,
             status_code=status.HTTP_201_CREATED)
def create_comment(photo_id: str, payload: CommentCreate, principal: CsrfPrincipal,
                   db: Db, _limited: CommentLimited) -> Comment:
    AuthService.require(principal, "comment.create")
    photo = db.get(Photo, photo_id)
    if photo is None or photo.status != "published":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "照片不存在或尚未发布")
    now = utc_now()
    comment = Comment(
        id=f"cmt_{uuid4().hex}", photo_id=photo_id,
        author_user_id=principal.user.id, body=payload.body,
        status="published", deletion_reason=None, deleted_at=None, deleted_by=None,
        created_at=now, updated_at=now,
    )
    db.add(comment)
    db.commit()
    return comment


@router.post("/{comment_id}/withdraw", response_model=CommentResponse)
def withdraw_comment(comment_id: str, principal: CsrfPrincipal, db: Db) -> Comment:
    AuthService.require(principal, "comment.withdraw.own")
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "评论不存在")
    if comment.author_user_id != principal.user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "只能撤回自己的评论")
    if comment.status != "published":
        raise HTTPException(status.HTTP_409_CONFLICT, "评论当前无法撤回")
    comment.status, comment.updated_at = "withdrawn", utc_now()
    AuthService(db).audit(principal.user.id, "comment.withdraw", "comment", comment.id)
    db.commit()
    return comment


@router.delete("/{comment_id}", response_model=CommentResponse)
def delete_comment(comment_id: str, payload: CommentDelete, principal: CsrfPrincipal,
                   db: Db) -> Comment:
    AuthService.require(principal, "comment.delete.any")
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "评论不存在")
    if comment.status == "deleted":
        raise HTTPException(status.HTTP_409_CONFLICT, "评论已经删除")
    now = utc_now()
    comment.status, comment.deletion_reason = "deleted", payload.reason
    comment.deleted_at, comment.deleted_by, comment.updated_at = now, principal.user.id, now
    AuthService(db).audit(principal.user.id, "comment.delete", "comment", comment.id,
                          {"reason": payload.reason} if payload.reason else {})
    db.commit()
    return comment
