"""验证单世界管理表单与合法日期选项。"""

import json
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from playwright.sync_api import Route, sync_playwright


SESSION = {
    "user": {
        "id": "usr-test",
        "username": "admin",
        "display_name": "档案管理员",
        "role": "admin",
        "player_id": None,
        "permissions": [],
    },
    "csrf_token": "test-csrf",
    "expires_at": "2099-01-01T00:00:00",
}


def api_stub(route: Route) -> None:
    """为纯界面测试返回最小管理 API 数据。"""

    path = urlparse(route.request.url).path.removeprefix("/api")
    if path in {"/auth/session", "/auth/login"}:
        payload: object = SESSION
    elif path == "/manage/photos":
        payload = [
            {
                "id": "photo-test",
                "title": "烟花映过门楼",
                "asset_id": "media-test",
                "captured_at": "2026-09-06T12:00:00",
            }
        ]
    else:
        payload = []
    route.fulfill(
        status=200,
        content_type="application/json",
        headers={
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Credentials": "true",
        },
        body=json.dumps(payload, ensure_ascii=False),
    )


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    console_errors: list[str] = []
    page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
    page.route("http://localhost:8000/api/**", api_stub)

    page.goto("http://localhost:3000/manage/media")
    page.wait_for_load_state("networkidle")
    page.locator('input[type="file"]').set_input_files(
        {"name": "2026-09-06_17.16.37.png", "mimeType": "image/png", "buffer": b"test"}
    )
    assert page.locator('select[aria-label="年"]').input_value() == "2026"
    assert page.locator('select[aria-label="月"]').input_value() == "09"
    assert page.locator('select[aria-label="日"]').input_value() == "06"
    assert page.locator('select[aria-label="时"]').count() == 0
    assert page.locator('select[aria-label="分"]').count() == 0

    page.locator('input[type="file"]').set_input_files(
        {"name": "spawn-overlook.png", "mimeType": "image/png", "buffer": b"test"}
    )
    today = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    assert "-".join([
        page.locator('select[aria-label="年"]').input_value(),
        page.locator('select[aria-label="月"]').input_value(),
        page.locator('select[aria-label="日"]').input_value(),
    ]) == today

    page.locator('select[aria-label="年"]').select_option("2026")
    page.locator('select[aria-label="月"]').select_option("02")
    assert page.locator('select[aria-label="日"] option:not([disabled])').count() == 28
    assert page.locator('select[aria-label="月"] option:not([disabled])').count() == 12

    page.goto("http://localhost:3000/manage/photos")
    page.wait_for_load_state("networkidle")
    assert page.get_by_label("稳定 ID").count() == 0
    assert page.get_by_label("周目 ID").count() == 0
    assert page.get_by_text("档案 ID 由系统保存时自动生成").count() == 1

    page.goto("http://localhost:3000/manage/login")
    page.get_by_label("用户名").fill("admin")
    page.get_by_label("密码").fill("test-password")
    page.locator("form").get_by_role("button", name="登录", exact=True).click()
    page.wait_for_url("**/manage")
    page.get_by_role("link", name="作品集", exact=True).click()
    page.wait_for_url("**/manage/stories")
    page.wait_for_load_state("networkidle")
    assert page.get_by_label("稳定 ID").count() == 0
    assert page.get_by_label("地点 ID").count() == 0
    assert page.get_by_label("事件 ID").count() == 0
    assert page.get_by_label("区块 ID").count() == 0
    cover_option = page.get_by_label("封面照片").locator("option").filter(has_text="烟花映过门楼")
    page.wait_for_timeout(1000)
    assert cover_option.count() == 1, console_errors
    page.get_by_role("button", name="添加宽幅图片").click()
    page.wait_for_timeout(100)
    photo_option = page.locator(".manage-blocks article select").nth(1).locator("option").filter(has_text="烟花映过门楼")
    assert photo_option.count() == 1
    assert not console_errors, console_errors
    browser.close()
