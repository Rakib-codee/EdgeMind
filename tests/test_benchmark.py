"""Regression tests for benchmark execution fairness.

Guards against the fixed bug where baseline executed on static node
profiles while adaptive executed on dynamic states, making comparisons
unfair.
"""

from app.models.task import TaskRequest
from app.scheduler.environment import NodeState
from benchmarks import run_benchmark

TASK = TaskRequest(task_id="t0", compute_units=10, max_latency_ms=1000)


def _capture_execution_node(monkeypatch, policy: str):
    captured = {}
    real = run_benchmark.simulate_execution

    def spy(task, node, rng=None):
        captured["node"] = node
        return real(task, node, rng=rng)

    monkeypatch.setattr(run_benchmark, "simulate_execution", spy)
    rows = run_benchmark.run_policy(policy, [TASK], seed=42)
    return captured, rows[0]


def test_baseline_executes_on_dynamic_node_state(monkeypatch):
    captured, row = _capture_execution_node(monkeypatch, "baseline")
    assert row["rejected"] is False
    assert isinstance(captured["node"], NodeState)


def test_adaptive_executes_on_dynamic_node_state(monkeypatch):
    captured, row = _capture_execution_node(monkeypatch, "adaptive")
    assert row["rejected"] is False
    assert isinstance(captured["node"], NodeState)


def test_decision_log_fields_are_recorded():
    rows = run_benchmark.run_policy("baseline", [TASK], seed=42)
    row = rows[0]
    assert row["estimated_latency_ms"] != ""
    assert row["failure_probability"] != ""
    assert row["queue_length"] != ""
    assert row["load_factor"] != ""


def test_rejected_task_has_empty_measurements():
    impossible = TaskRequest(
        task_id="tx", compute_units=10, max_latency_ms=0.0001
    )
    rows = run_benchmark.run_policy("baseline", [impossible], seed=42)
    row = rows[0]
    assert row["rejected"] is True
    assert row["selected_target"] == ""
    assert row["total_latency_ms"] == ""
    assert row["estimated_latency_ms"] == ""
