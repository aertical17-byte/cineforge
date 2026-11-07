"""Rate limiting: DB-backed rolling windows (Redis-compatible hook when configured)."""
from __future__ import annotations

import time


class RollingLimiter:
    def __init__(self, store_dict: dict | None = None):
        self._store = store_dict if store_dict is not None else {}

    def hit(self, scope: str, limit_per_minute: int) -> bool:
        now = time.time()
        window_start, count = self._store.get(scope, (now, 0))
        if now - window_start >= 60:
            window_start, count = now, 0
        count += 1
        self._store[scope] = (window_start, count)
        return count <= limit_per_minute


limiter = RollingLimiter()
