"""账号、会话和权限数据库访问。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, UserPermission, UserSession


class UserRepository:
    """封装认证和授权所需的账号查询。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def by_username(self, username: str) -> User | None:
        return self.db.scalar(select(User).where(User.username == username))

    def by_id(self, user_id: str) -> User | None:
        return self.db.get(User, user_id)

    def permissions(self, user_id: str) -> set[str]:
        values = self.db.scalars(
            select(UserPermission.permission).where(UserPermission.user_id == user_id)
        )
        return set(values)

    def session_by_hash(self, token_hash: str) -> UserSession | None:
        return self.db.scalar(select(UserSession).where(UserSession.token_hash == token_hash))
