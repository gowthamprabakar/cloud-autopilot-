"""
Simple in-memory rate limiter using a sliding window counter.
Not suitable for multi-process deployments (use Redis in production).
For dev/staging, this provides basic brute-force protection.
"""

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request
from starlette import status

_windows: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


def reset_for_testing() -> None:
    """Clear all rate-limit windows.  Call from test fixtures only."""
    with _lock:
        _windows.clear()


def rate_limit(max_calls: int, window_seconds: int = 60):
    """
    Dependency factory. Usage:
        @router.post("/login")
        async def login(req: ..., _: None = Depends(rate_limit(10, 60))):
    """

    async def _check(request: Request):
        # If client is unavailable (e.g. ASGI test transport), skip rate limiting
        if request.client is None:
            return
        key = f"{request.client.host}:{request.url.path}"
        now = time.time()
        cutoff = now - window_seconds
        with _lock:
            calls = _windows[key]
            # remove expired
            _windows[key] = [t for t in calls if t > cutoff]
            if len(_windows[key]) >= max_calls:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: max {max_calls} requests per {window_seconds}s",
                    headers={"Retry-After": str(window_seconds)},
                )
            _windows[key].append(now)

    return _check
