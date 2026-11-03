"""单实例部署适用的轻量内存限流。"""

from collections import defaultdict, deque
from collections.abc import Callable
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request, status

_events: dict[str, deque[float]] = defaultdict(deque)
_lock = Lock()


def limit(scope: str, attempts: int, window_seconds: int) -> Callable[[Request], None]:
    """创建按客户端地址和操作范围计数的 FastAPI 依赖。"""

    def check(request: Request) -> None:
        address = request.client.host if request.client else "unknown"
        key = f"{scope}:{address}"
        now = monotonic()
        with _lock:
            bucket = _events[key]
            while bucket and bucket[0] <= now - window_seconds:
                bucket.popleft()
            if len(bucket) >= attempts:
                raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "操作过于频繁，请稍后再试")
            bucket.append(now)

    return check
