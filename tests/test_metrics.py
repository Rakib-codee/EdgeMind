"""Tests for the Prometheus /metrics endpoint."""

from starlette.testclient import TestClient

from app.main import app
from app.monitoring import metrics

client = TestClient(app)

TASK = {
    "task_id": "metrics-test-1",
    "compute_units": 100,
    "max_latency_ms": 5000,
}


def test_metrics_endpoint_exposes_prometheus_format():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]


def test_execute_updates_execution_metrics():
    def executed_count():
        body = client.get("/metrics").text
        return sum(
            1
            for line in body.splitlines()
            if line.startswith("edgemind_tasks_executed_total{")
        )

    before = executed_count()
    response = client.post("/execute", json=TASK)
    assert response.status_code == 200
    assert executed_count() == before + 1


def test_metrics_output_contains_edgemind_metrics():
    client.post("/execute", json=TASK)
    body = client.get("/metrics").text
    assert "edgemind_tasks_executed_total" in body
    assert "edgemind_task_latency_ms" in body
    assert "edgemind_tasks_scheduled_total" in body


def test_schedule_failure_updates_failure_counter():
    before = sum(
        s.value for s in metrics.SCHEDULE_FAILURES.collect()[0].samples
    )
    impossible = {**TASK, "task_id": "metrics-impossible", "max_latency_ms": 0.0001}
    response = client.post("/schedule", json=impossible)
    assert response.status_code == 422
    after = sum(
        s.value for s in metrics.SCHEDULE_FAILURES.collect()[0].samples
    )
    assert after == before + 1
