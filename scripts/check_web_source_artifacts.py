"""阻止 TypeScript 编译产物写入 Nuxt 源码目录并覆盖源码解析。"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_APP_ROOT = PROJECT_ROOT / "apps" / "web" / "app"


def source_for(generated: Path) -> Path | None:
    """仅识别旁边确有 .ts 或 .vue 源文件的可疑 JavaScript 产物。"""

    without_js = generated.with_suffix("")
    if without_js.exists():
        return without_js
    typescript_source = without_js.with_suffix(".ts")
    return typescript_source if typescript_source.exists() else None


def main() -> int:
    artifacts = [
        (path, source)
        for path in WEB_APP_ROOT.rglob("*.js")
        if (source := source_for(path)) is not None
    ]
    if not artifacts:
        print("前端源码产物检查通过。")
        return 0

    print("检测到源码旁的 JavaScript 编译产物；请删除后再运行 Nuxt：")
    for artifact, source in artifacts:
        print(
            f"- {artifact.relative_to(PROJECT_ROOT)} "
            f"（源码：{source.relative_to(PROJECT_ROOT)}）"
        )
    print("请仅使用 npm run typecheck:web 进行无输出类型检查。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
