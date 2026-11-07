"""认证、注册审批、角色与权限 API 契约。"""

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=200)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    display_name: str = Field(min_length=1, max_length=80)
    minecraft_name: str = Field(min_length=3, max_length=16, pattern=r"^[a-zA-Z0-9_]+$")
    application_reason: str = Field(min_length=1, max_length=1000)
    password: str = Field(min_length=8, max_length=200)
    website: str = Field(default="", max_length=200, exclude=True)

    @field_validator("password")
    @classmethod
    def password_has_letter_and_number(cls, value: str) -> str:
        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValueError("密码至少包含一个字母和一个数字")
        return value


class RegistrationResponse(BaseModel):
    status: str = "pending"
    message: str


class SessionUser(BaseModel):
    id: str
    username: str
    display_name: str
    role: str
    role_name: str
    status: str
    player_id: str | None
    permissions: list[str]


class SessionResponse(BaseModel):
    user: SessionUser
    csrf_token: str
    expires_at: datetime


class PermissionSummary(BaseModel):
    code: str
    name_zh: str
    group_name: str
    description: str


class RoleSummary(BaseModel):
    id: str
    code: str
    name_zh: str
    description: str
    permissions: list[str]


class RolePermissionUpdate(BaseModel):
    permissions: list[str] = Field(max_length=40)

    @field_validator("permissions")
    @classmethod
    def permissions_are_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("权限不能重复")
        return value


class UserSummary(BaseModel):
    id: str
    username: str
    display_name: str
    minecraft_name: str | None
    application_reason: str
    review_reason: str | None
    ban_reason: str | None
    role_id: str
    role: str
    role_name: str
    status: str
    player_id: str | None
    permissions: list[str]
    created_at: datetime


class UserReviewRequest(BaseModel):
    action: str = Field(pattern=r"^(approve|reject)$")
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def rejection_has_reason(self) -> "UserReviewRequest":
        if self.action == "reject" and not (self.reason or "").strip():
            raise ValueError("拒绝申请时需要填写原因")
        return self


class UserRoleUpdate(BaseModel):
    role_id: str = Field(min_length=1, max_length=40)


class UserBanUpdate(BaseModel):
    banned: bool
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def ban_has_reason(self) -> "UserBanUpdate":
        if self.banned and not (self.reason or "").strip():
            raise ValueError("封禁账号时需要填写原因")
        return self
