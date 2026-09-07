"""
Test Server-Sent Events (SSE) stream endpoint for live sovereignty audit feed.
"""

import json
import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from security.network_proof import get_sentinel


def test_sse_endpoint_connects():
    """Validates SSE stream connection with max_events=1 for clean termination."""
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/sovereignty/stream?max_events=1")
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        body = response.text
        assert "event: connected" in body
        assert "STREAM_CONNECTED" in body


def test_sentinel_subscriber_receives_audit_block():
    """Validates sentinel listener callback receives audit block on cycle."""
    sentinel = get_sentinel()
    received = []

    def callback(entry):
        received.append(entry)

    sentinel.subscribe(callback)
    try:
        sentinel.audit_cycle("SSE_SUBSCRIBER_TEST_STAGE")
        assert len(received) >= 1
        assert received[-1]["stage"] == "SSE_SUBSCRIBER_TEST_STAGE"
    finally:
        sentinel.unsubscribe(callback)


def test_sse_disabled_on_multi_worker(monkeypatch):
    """When WEB_CONCURRENCY > 1, lifespan disables SSE and route returns HTTP 503."""
    monkeypatch.setenv("WEB_CONCURRENCY", "2")
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/sovereignty/stream")
        assert response.status_code == 503
        assert "multi-worker" in response.json()["detail"]
