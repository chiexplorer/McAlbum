"""媒体上传额度按账号与角色隔离。"""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.routes import media as media_routes
from app.core.config import Settings


def principal(user_id: str, *, is_admin: bool) -> SimpleNamespace:
    """构造限流测试所需的最小身份对象。"""

    return SimpleNamespace(user=SimpleNamespace(id=user_id), is_admin=is_admin)


def test_upload_limit_uses_user_id_and_role_quota(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        media_routes,
        "get_settings",
        lambda: SimpleNamespace(
            media_upload_limit_user=20,
            media_upload_limit_admin=100,
        ),
    )
    marker = uuid4().hex
    user = principal(f"user-{marker}", is_admin=False)
    another_user = principal(f"another-{marker}", is_admin=False)
    admin = principal(f"admin-{marker}", is_admin=True)

    for _ in range(20):
        media_routes.check_upload_limit(user)  # type: ignore[arg-type]
    with pytest.raises(HTTPException) as user_error:
        media_routes.check_upload_limit(user)  # type: ignore[arg-type]
    assert user_error.value.status_code == 429

    # 同一出口 IP 下的另一个账号不应继承前一账号的计数。
    media_routes.check_upload_limit(another_user)  # type: ignore[arg-type]

    for _ in range(100):
        media_routes.check_upload_limit(admin)  # type: ignore[arg-type]
    with pytest.raises(HTTPException) as admin_error:
        media_routes.check_upload_limit(admin)  # type: ignore[arg-type]
    assert admin_error.value.status_code == 429


def test_upload_quotas_can_be_configured_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCALBUM_MEDIA_UPLOAD_LIMIT_USER", "24")
    monkeypatch.setenv("MCALBUM_MEDIA_UPLOAD_LIMIT_ADMIN", "120")

    settings = Settings(_env_file=None)

    assert settings.media_upload_limit_user == 24
    assert settings.media_upload_limit_admin == 120
