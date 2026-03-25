"""
Prometheus metrics registry.
Defines all counters and histograms. Import from here, never create new metrics inline.
"""
from prometheus_client import Counter, Histogram, CollectorRegistry, REGISTRY

# HTTP request counter — labels: method, path (normalised), status_code
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)

# HTTP request latency histogram — labels: method, path
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Active requests gauge (optional but useful)
http_requests_inprogress = Counter(
    "http_requests_inprogress_total",
    "Count of in-progress HTTP requests",
    ["method", "path"],
)
