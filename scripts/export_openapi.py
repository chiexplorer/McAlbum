"""将 FastAPI OpenAPI 契约稳定写入 contracts/openapi。"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
sys.path.insert(0, str(API_ROOT))

from app.main import app  # noqa: E402

output = ROOT / "contracts" / "openapi" / "mcalbum-api.json"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(
    json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(f"OpenAPI 快照已写入：{output.relative_to(ROOT)}")
