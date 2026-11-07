"""认证与内容契约的无数据库单元测试。"""

import pytest
from pydantic import ValidationError

from app.core.security import hash_password, secret_hash, secrets_equal, verify_password
from app.schemas.auth import RegisterRequest
from app.schemas.content import PhotoWrite, StoryWrite
from app.services.auth import ALLOWED_PERMISSIONS
from app.services.content import new_photo_id


def test_argon2id_password_round_trip() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert password_hash.startswith("$argon2id$")
    assert verify_password(password_hash, "correct horse battery staple")
    assert not verify_password(password_hash, "wrong password")


def test_secret_hash_comparison() -> None:
    digest = secret_hash("session-token")

    assert secrets_equal(digest, secret_hash("session-token"))
    assert not secrets_equal(digest, secret_hash("other-token"))


def test_permissions_remain_fixed_and_small() -> None:
    assert "photo.create" in ALLOWED_PERMISSIONS
    assert "photo.publish.own" in ALLOWED_PERMISSIONS
    assert all("*" not in permission for permission in ALLOWED_PERMISSIONS)


def test_registration_password_requires_letter_and_number() -> None:
    common = {
        "username": "test-user",
        "display_name": "测试玩家",
        "minecraft_name": "Test_Player",
        "application_reason": "服务器成员",
    }
    with pytest.raises(ValidationError):
        RegisterRequest.model_validate({**common, "password": "12345678"})
    with pytest.raises(ValidationError):
        RegisterRequest.model_validate({**common, "password": "abcdefgh"})
    assert RegisterRequest.model_validate({**common, "password": "abcd1234"})


def test_photo_ids_are_generated_and_url_safe() -> None:
    first = new_photo_id()
    second = new_photo_id()

    assert first.startswith("photo-")
    assert len(first) == len("photo-") + 32
    assert first != second


def test_photo_description_is_optional_and_tags_are_normalized() -> None:
    photo = PhotoWrite.model_validate(
        {
            "title": "测试照片",
            "asset_id": "media-test",
            "captured_at": "2026-10-01T12:00:00+08:00",
            "tags": [" 夜景 ", "夜景", "  主城   建筑  "],
        }
    )

    assert photo.description == ""
    assert photo.tags == ["夜景", "主城 建筑"]


def test_story_rejects_duplicate_section_ids() -> None:
    with pytest.raises(ValidationError, match="唯一"):
        StoryWrite.model_validate(
            {
                "id": "test-story",
                "title": "测试作品集",
                "summary": "用于验证区块 ID。",
                "cover_asset_id": "media-test",
                "sections": [
                    {"id": "opening", "type": "text", "body": "第一段"},
                    {"id": "opening", "type": "text", "body": "第二段"},
                ],
            }
        )
