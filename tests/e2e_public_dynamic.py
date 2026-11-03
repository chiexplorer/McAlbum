"""验证已发布数据库照片可在不重建前端的情况下进入公开页面。"""

import json
import urllib.request

from playwright.sync_api import sync_playwright

API_URL = "http://localhost:8000/api/public/photos"
WEB_URL = "http://localhost:3000"


def main() -> None:
    with urllib.request.urlopen(API_URL, timeout=10) as response:  # noqa: S310
        photos = json.load(response)
    if not photos:
        raise RuntimeError("公开 API 中没有可用于端到端验证的已发布照片")

    latest = photos[0]["photo"]
    errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "response",
            lambda response: errors.append(f"HTTP {response.status}: {response.url}")
            if response.status >= 400 and "/auth/session" not in response.url
            else None,
        )

        page.goto(f"{WEB_URL}/album", wait_until="networkidle")
        page.get_by_role("heading", name=latest["title"]).wait_for()

        page.goto(f"{WEB_URL}/photos/{latest['id']}", wait_until="networkidle")
        page.get_by_role("heading", name=latest["title"], exact=True).wait_for()
        browser.close()

    if errors:
        raise RuntimeError(f"浏览器控制台出现错误：{errors}")
    print(f"动态公开内容验证通过：{latest['id']} · {latest['title']}")


if __name__ == "__main__":
    main()
