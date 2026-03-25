"""Tests for Prometheus metrics endpoint."""
import pytest

pytestmark = pytest.mark.asyncio

async def test_metrics_endpoint_returns_200(client):
    """GET /metrics returns 200 with prometheus text content."""
    res = await client.get("/metrics")
    assert res.status_code == 200
    assert "text/plain" in res.headers["content-type"]

async def test_metrics_contains_request_counter(client):
    """After making a request, http_requests_total counter appears in /metrics."""
    # Make a request first
    await client.get("/health")
    res = await client.get("/metrics")
    assert res.status_code == 200
    # Prometheus text format uses metric name as prefix
    assert "http_requests_total" in res.text

async def test_metrics_contains_latency_histogram(client):
    """http_request_duration_seconds histogram appears in /metrics."""
    await client.get("/health")
    res = await client.get("/metrics")
    assert "http_request_duration_seconds" in res.text

async def test_health_endpoint_returns_ok(client):
    """GET /health returns {status: ok}."""
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
