"""使用 Chromium 验收 McAlbum 静态站的核心浏览路径与体验边界。"""

from __future__ import annotations

import contextlib
import re
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "apps" / "web" / ".output" / "public"
SCREENSHOT = ROOT / "test-results" / "e2e-failure.png"


class StaticHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, directory=str(PUBLIC), **kwargs)

    def log_message(self, format: str, *args: object) -> None:
        return

    def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None:
        if code == 404 and (PUBLIC / "404.html").is_file():
            body = (PUBLIC / "404.html").read_bytes()
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().send_error(code, message, explain)


class StaticServer(ThreadingHTTPServer):
    """提高 Windows 下并发加载 Nuxt 分块时的连接队列容量。"""

    request_queue_size = 128
    daemon_threads = True


def open_page(page: Page, base_url: str, path: str) -> None:
    response = page.goto(f"{base_url}{path}")
    page.wait_for_load_state("networkidle")
    assert response is not None and response.ok, f"{path} 返回 {response.status if response else '无响应'}"
    assert page.locator("h1").count() == 1, f"{path} 应有且仅有一个 h1"


def stub_public_api(page: Page) -> None:
    """静态验收显式模拟 API 不可用，确认页面会保留离线快照。"""

    page.route(
        re.compile(
            r"^http://(?:localhost|127\.0\.0\.1):8000/api/public/(?:photos|stories)(?:/.*)?$"
        ),
        lambda route: route.fulfill(status=200, content_type="application/json", body="{}"),
    )
    page.route(
        re.compile(r"^http://(?:localhost|127\.0\.0\.1):8000/api/auth/session$"),
        lambda route: route.fulfill(status=204),
    )


def main() -> int:
    if not PUBLIC.is_dir():
        print("静态产物不存在，请先运行 npm run generate:web")
        return 1

    server = StaticServer(("127.0.0.1", 0), StaticHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    errors: list[str] = []
    requests: list[str] = []
    page: Page | None = None

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 960})
            stub_public_api(page)
            page.on(
                "console",
                lambda message: errors.append(f"{page.url}: {message.text}")
                if message.type == "error"
                else None,
            )
            page.on("pageerror", lambda error: errors.append(f"{page.url}: {error}"))
            page.on(
                "requestfailed",
                lambda request: errors.append(
                    f"{page.url}: 请求失败 {request.url} · {request.failure}"
                ),
            )
            page.on("request", lambda request: requests.append(request.url))

            for path in ("/", "/album", "/stories", "/players"):
                open_page(page, base_url, path)

            open_page(page, base_url, "/")
            assert page.locator(".principles-section li").count() == 3
            assert page.locator(".image-comparison > div").count() == 2
            initial_transfer_bytes = page.evaluate(
                "performance.getEntriesByType('resource')"
                ".reduce((total, entry) => total + entry.encodedBodySize, 0)"
            )
            assert initial_transfer_bytes <= 2 * 1024 * 1024, (
                f"首页初始资源超过 2 MiB：{initial_transfer_bytes} bytes"
            )
            page.keyboard.press("Home")
            page.keyboard.press("Tab")
            assert page.locator(":focus").get_attribute("class") == "skip-link"

            open_page(page, base_url, "/album")
            page.get_by_role("button", name="夜景", exact=True).click()
            page.wait_for_url("**/album?tag=**")
            assert "tag=" in page.url
            page.reload()
            page.wait_for_load_state("networkidle")
            assert page.get_by_role("button", name="夜景", exact=True).get_attribute("aria-pressed") == "true"
            page.go_back()
            page.wait_for_load_state("networkidle")
            assert "tag=" not in page.url

            first_photo_button = page.locator(".justified-photo__media").first
            first_photo_button.focus()
            first_photo_button.click()
            assert page.locator("dialog[open]").count() == 1
            page.keyboard.press("Escape")
            assert page.locator("dialog[open]").count() == 0
            assert page.locator(":focus").evaluate(
                "element => element === document.querySelector('.justified-photo__media')"
            )

            open_page(page, base_url, "/photos/mid-autumn-fireworks-03")
            download = page.get_by_role("link", name="下载原图", exact=True)
            assert download.count() == 1
            assert download.get_attribute("href").startswith("/originals/")
            assert download.get_attribute("download") is not None

            open_page(page, base_url, "/players")
            assert page.get_by_text("玩家档案等待本人确认").count() == 1

            reduced = browser.new_page(reduced_motion="reduce")
            stub_public_api(reduced)
            open_page(reduced, base_url, "/")
            assert reduced.evaluate("getComputedStyle(document.documentElement).scrollBehavior") == "auto"
            reduced.close()

            mobile = browser.new_page(viewport={"width": 390, "height": 844})
            stub_public_api(mobile)
            for path in ("/", "/album", "/stories", "/players"):
                open_page(mobile, base_url, path)
                assert mobile.evaluate(
                    "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
                ), f"{path} 在 390px 下出现横向溢出"
            mobile.goto(f"{base_url}/")
            mobile.wait_for_load_state("networkidle")
            mobile.locator(".mobile-nav summary").click()
            assert mobile.get_by_role("link", name="历史", exact=True).count() == 1
            mobile.close()

            assert not errors, f"浏览器控制台错误：{errors}"
            assert not any("originals" in request or "yang/files" in request for request in requests)
            assert not any(request.lower().endswith((".png", ".jpg", ".jpeg")) for request in requests)

            response = page.goto(f"{base_url}/missing-archive")
            page.wait_for_load_state("networkidle")
            assert response is not None and response.status == 404
            assert page.get_by_text("这位迷路的玩家没有找到档案").count() == 1
            browser.close()
    except Exception:
        SCREENSHOT.parent.mkdir(parents=True, exist_ok=True)
        if page is not None:
            with contextlib.suppress(Exception):
                page.screenshot(path=str(SCREENSHOT), full_page=True)
        raise
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    print("静态站浏览器验收通过：核心路径、键盘、移动端、减少动效与媒体请求边界均符合预期。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
