"""账号、会话和权限数据库访问。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Permission, Role, RolePermission, User, UserSession


class UserRepository:
    """封装认证和授权所需的账号查询。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def by_username(self, username: str) -> User | None:
        return self.db.scalar(select(User).where(User.username == username))

    def by_id(self, user_id: str) -> User | None:
        return self.db.get(User, user_id)

    def by_minecraft_name(self, minecraft_name: str) -> User | None:
        return self.db.scalar(select(User).where(User.minecraft_name == minecraft_name))

    def permissions(self, user_id: str) -> set[str]:
        values = self.db.scalars(
            select(RolePermission.permission_code)
            .join(User, User.role_id == RolePermission.role_id)
            .where(User.id == user_id)
        )
        return set(values)

    def role(self, user: User) -> Role:
        role = self.db.get(Role, user.role_id)
        if role is None:
            raise RuntimeError(f"用户 {user.id} 缺少角色")
        return role

    def role_by_code(self, code: str) -> Role | None:
        return self.db.scalar(select(Role).where(Role.code == code))

    def roles(self) -> list[Role]:
        return list(self.db.scalars(select(Role).order_by(Role.id)))

    def permission_catalog(self) -> list[Permission]:
        return list(self.db.scalars(select(Permission).order_by(Permission.sort_order)))

    def session_by_hash(self, token_hash: str) -> UserSession | None:
        return self.db.scalar(select(UserSession).where(UserSession.token_hash == token_hash))
