import random

from app.models.task import TaskRequest
from app.scheduler import DEFAULT_NODES
from app.workers.simulated_worker import simulate_execution


def make_task(compute_units=100, max_latency_ms=5000, task_id="w1"):
    return TaskRequest(
        task_id=task_id,
        compute_units=compute_units,
        max_latency_ms=max_latency_ms,
    )


def node_by_name(name):
    return next(n for n in DEFAULT_NODES if n.name == name)


def test_execution_returns_result_with_expected_fields():
    task = make_task()
    result = simulate_execution(task, node_by_name("edge"), rng=random.Random(7))
    assert result.task_id == "w1"
    assert result.target == "edge"
    assert result.success in (True, False)
    assert result.total_latency_ms > 0
    assert result.deadline_met in (True, False)


def test_execution_is_deterministic_with_same_seed():
    task = make_task()
    node = node_by_name("cloud")
    first = simulate_execution(task, node, rng=random.Random(42))
    second = simulate_execution(task, node, rng=random.Random(42))
    assert first.model_dump() == second.model_dump()


def test_total_latency_is_network_plus_compute():
    rng = random.Random(3)
    task = make_task(compute_units=0.0001)
    result = simulate_execution(task, node_by_name("edge"), rng=rng)
    expected = (
        result.network_latency_ms + result.compute_duration_ms
    )
    assert abs(result.total_latency_ms - expected) < 0.01


def test_deadline_miss_detected():
    task = make_task(compute_units=100000, max_latency_ms=1)
    result = simulate_execution(task, node_by_name("local"), rng=random.Random(1))
    assert result.deadline_met is False
