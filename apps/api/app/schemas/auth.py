"""认证、账号和权限 API 契约。"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=10, max_length=200)


class RegisterRequest(LoginRequest):
    display_name: str = Field(min_length=1, max_length=80)
    invitation_code: str = Field(min_length=20, max_length=200)


class SessionUser(BaseModel):
    id: str
    username: str
    display_name: str
    role: str
    player_id: str | None
    permissions: list[str]


class SessionResponse(BaseModel):
    user: SessionUser
    csrf_token: str
    expires_at: datetime


class InvitationCreate(BaseModel):
    expires_in_hours: int = Field(default=72, ge=1, le=720)
    permissions: list[str] = Field(default_factory=list, max_length=20)


class InvitationCreated(BaseModel):
    code: str
    expires_at: datetime


class UserPermissionUpdate(BaseModel):
    permissions: list[str] = Field(max_length=20)

    @field_validator("permissions")
    @classmethod
    def permissions_are_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("权限不能重复")
        return value


class UserSummary(SessionUser):
    enabled: bool
    created_at: datetime


class UserStatusUpdate(BaseModel):
    enabled: bool
