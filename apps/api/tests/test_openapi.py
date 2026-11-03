"""确保协作 API 的关键边界进入 OpenAPI 契约。"""

from app.main import app


def test_collaboration_routes_are_documented() -> None:
    paths = app.openapi()["paths"]

    assert "/api/auth/login" in paths
    assert "/api/manage/media" in paths
    assert "/api/manage/photos/{item_id}/transition" in paths
    assert "/api/manage/stories/{item_id}/transition" in paths
    assert "/api/admin/users/{user_id}/permissions" in paths
    assert "/api/admin/publish" in paths
    assert "/api/public/photos" in paths
    assert "/api/public/photos/feed" in paths
    assert "/api/public/photos/timeline" in paths
    assert "/api/public/photos/{photo_id}" in paths
    assert "/api/public/stories" in paths
    assert "/api/public/stories/{story_id}" in paths
