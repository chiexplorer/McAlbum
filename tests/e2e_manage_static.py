"""不依赖数据库的管理端登录页浏览器冒烟检查。"""

from playwright.sync_api import sync_playwright


def check_page(page, viewport_name: str) -> None:
    errors: list[str] = []
    page.on(
        "console",
        lambda message: errors.append(message.text) if message.type == "error" else None,
    )
    page.route(
        "**/api/auth/session",
        lambda route: route.fulfill(status=204, body=""),
    )
    page.goto("http://localhost:3000/manage/login")
    page.wait_for_load_state("networkidle")
    assert page.get_by_role("heading", name="进入档案编目室").is_visible()
    assert page.get_by_label("用户名").is_visible()
    assert page.get_by_label("密码").is_visible()
    page.get_by_role("button", name="使用邀请码").click()
    assert page.get_by_label("公开称呼").is_visible()
    assert page.get_by_label("邀请码").is_visible()
    overflow = page.evaluate(
        "document.documentElement.scrollWidth > document.documentElement.clientWidth"
    )
    assert not overflow, f"{viewport_name} 出现横向溢出"
    assert not errors, f"{viewport_name} 控制台错误：{errors}"


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    desktop = browser.new_page(viewport={"width": 1440, "height": 900})
    check_page(desktop, "desktop")
    mobile = browser.new_page(viewport={"width": 390, "height": 844})
    check_page(mobile, "mobile")
    browser.close()

print("管理端登录页桌面与移动端冒烟检查通过。")
