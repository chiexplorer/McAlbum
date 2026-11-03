"""验证作品集可在不重建静态站点时通过公开 API 出现在列表和详情页。"""

import json
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Route, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ASSET = json.loads(
    (ROOT / "apps/web/app/generated/media-assets.json").read_text(encoding="utf-8")
)[0]
STORY = {
    "id": "story-dynamic-test",
    "title": "动态发布专题",
    "summary": "这篇作品集只存在于动态 API 响应中。",
    "coverAssetId": ASSET["id"],
    "playerIds": [],
    "sections": [
        {
            "id": "section-dynamic-test",
            "type": "text",
            "body": "刷新作品集页面后，无需重建即可读到这段正文。",
        }
    ],
    "status": "published",
    "isMock": False,
}


def public_story_stub(route: Route) -> None:
    path = urlparse(route.request.url).path
    payload: object
    if path.endswith("/public/stories/story-dynamic-test"):
        payload = {"story": STORY, "assets": [ASSET]}
    else:
        payload = [{"story": STORY, "coverAsset": ASSET}]
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
    errors: list[str] = []
    page.on(
        "console",
        lambda message: errors.append(message.text) if message.type == "error" else None,
    )
    page.route("**/api/public/stories**", public_story_stub)

    page.goto("http://localhost:3000/stories")
    page.wait_for_load_state("networkidle")
    link = page.get_by_role("link", name="动态发布专题")
    link.wait_for()
    link.click()
    page.wait_for_url("**/stories/story-dynamic-test")
    page.wait_for_load_state("networkidle")
    heading = page.get_by_role("heading", name="动态发布专题")
    heading.wait_for()
    assert heading.is_visible()
    body = page.get_by_text("刷新作品集页面后，无需重建即可读到这段正文。")
    body.wait_for()
    assert body.is_visible()
    assert not errors, errors
    browser.close()

print("作品集动态列表与详情浏览器验证通过。")
