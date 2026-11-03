"""为静态发布快照生成可审计、可复核的 SHA-256 清单。"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "apps" / "web" / ".output" / "public"
OUTPUT = ROOT / "apps" / "web" / ".output" / "release-manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def entries(root: Path, prefix: str) -> list[dict[str, object]]:
    return [
        {
            "path": f"{prefix}/{path.relative_to(root).as_posix()}",
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]


def main() -> None:
    if not PUBLIC.is_dir():
        raise SystemExit("静态产物不存在，请先运行 npm run generate:web")

    sources: list[dict[str, object]] = []
    for directory in (ROOT / "content", ROOT / "contracts" / "json-schema"):
        sources.extend(entries(directory, directory.relative_to(ROOT).as_posix()))
    for filename in ("package.json", "package-lock.json"):
        path = ROOT / filename
        sources.append({"path": filename, "bytes": path.stat().st_size, "sha256": sha256(path)})

    manifest = {
        "formatVersion": 1,
        "createdAt": datetime.now(UTC).isoformat(),
        "timeZone": "Asia/Shanghai",
        "sourceFiles": sources,
        "publicFiles": entries(PUBLIC, "public"),
    }
    OUTPUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"发布清单已生成：{OUTPUT.relative_to(ROOT)}，"
        f"记录 {len(sources)} 个源文件和 {len(manifest['publicFiles'])} 个公开文件。"
    )


if __name__ == "__main__":
    main()
