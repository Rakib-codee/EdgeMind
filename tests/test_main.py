from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "EdgeMind"


def test_schedule_selects_fastest_feasible_node():
    response = client.post(
        "/schedule",
        json={"task_id": "t1", "compute_units": 100, "max_latency_ms": 5000},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == "t1"
    assert body["selected_target"] in {"local", "edge", "cloud"}
    assert body["estimated_latency_ms"] > 0
    assert body["estimated_latency_ms"] <= 5000
    assert body["scheduler"] == "baseline"


def test_schedule_rejects_unfeasible_task():
    response = client.post(
        "/schedule",
        json={"task_id": "t2", "compute_units": 100000, "max_latency_ms": 1},
    )
    assert response.status_code == 422
    assert "No execution target" in response.json()["detail"]


def test_schedule_validates_request():
    response = client.post(
        "/schedule",
        json={"task_id": "t3", "compute_units": -5, "max_latency_ms": 100},
    )
    assert response.status_code == 422

    response = client.post("/schedule", json={"compute_units": 10})
    assert response.status_code == 422
