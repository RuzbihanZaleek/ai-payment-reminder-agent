"""Metrics registry + /metrics endpoint."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.metrics import (
    MetricsRegistry,
    metrics,
    record_api_request,
    record_workflow,
    record_payment_processed,
    record_reminder,
    record_notification_processed,
    record_notification_failed,
    record_notification_retry,
)
from app.api.health import router as health_router


def test_counter_increments():
    registry = MetricsRegistry()

    registry.inc("things_total")
    registry.inc("things_total", 2)

    assert registry.snapshot()["counters"]["things_total"] == 3


def test_summary_tracks_sum_and_count():
    registry = MetricsRegistry()

    registry.observe("dur_seconds", 0.5)
    registry.observe("dur_seconds", 1.5)

    snap = registry.snapshot()
    assert snap["summary_sum"]["dur_seconds"] == 2.0
    assert snap["summary_count"]["dur_seconds"] == 2


def test_render_prometheus_format():
    registry = MetricsRegistry()
    registry.inc("requests_total", help="Total requests")
    registry.observe("latency_seconds", 0.25, help="Latency")

    text = registry.render()

    assert "# TYPE requests_total counter" in text
    assert "requests_total 1.0" in text
    assert "# TYPE latency_seconds summary" in text
    assert "latency_seconds_sum 0.25" in text
    assert "latency_seconds_count 1" in text


def test_domain_recorders_increment_global_registry():
    metrics.reset()

    record_api_request(0.1)
    record_workflow(success=False, duration_seconds=0.2)
    record_payment_processed()
    record_reminder(sent=True)
    record_reminder(sent=False)

    record_notification_processed()
    record_notification_failed()
    record_notification_retry()
    record_notification_retry()

    snap = metrics.snapshot()
    assert snap["counters"]["api_requests_total"] == 1
    assert snap["counters"]["agent_workflow_executions_total"] == 1
    assert snap["counters"]["agent_workflow_failures_total"] == 1
    assert snap["counters"]["payments_processed_total"] == 1
    assert snap["counters"]["reminders_sent_total"] == 1
    assert snap["counters"]["reminders_failed_total"] == 1
    assert snap["counters"]["notification_outbox_processed_total"] == 1
    assert snap["counters"]["notification_outbox_failed_total"] == 1
    assert snap["counters"]["notification_outbox_retry_total"] == 2


def test_metrics_endpoint_returns_text():
    metrics.reset()
    record_payment_processed()

    app = FastAPI()
    app.include_router(health_router)
    client = TestClient(app)

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "payments_processed_total" in response.text
