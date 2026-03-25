"""
Starlette middleware that records Prometheus metrics for every HTTP request.
"""
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.metrics import http_requests_total, http_request_duration_seconds

# Paths that should not be tracked to avoid high-cardinality labels
_SKIP_PATHS = {"/metrics", "/health", "/favicon.ico"}

def _normalise_path(path: str) -> str:
    """Replace UUID segments with {id} to avoid label cardinality explosion."""
    import re
    # Replace UUID4 patterns
    path = re.sub(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        "{id}",
        path,
    )
    return path


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = _normalise_path(request.url.path)
        method = request.method

        if path in _SKIP_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        status_code = str(response.status_code)
        http_requests_total.labels(method=method, path=path, status_code=status_code).inc()
        http_request_duration_seconds.labels(method=method, path=path).observe(duration)

        return response
