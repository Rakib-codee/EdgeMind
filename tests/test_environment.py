import random

from app.models.task import TaskRequest
from app.scheduler import (
    DEFAULT_NODES,
    DynamicEnvironment,
    NodeState,
    estimate_latency_ms,
)
from app.workers.simulated_worker import failure_probability, simulate_execution


def make_task(compute_units=100, max_latency_ms=5000, task_id="e1"):
    return TaskRequest(
        task_id=task_id,
        compute_units=compute_units,
        max_latency_ms=max_latency_ms,
    )


def test_steady_state_matches_profile():
    env = DynamicEnvironment(DEFAULT_NODES, rng=random.Random(1))
    state = env.observe("edge")
    assert state.network_latency_ms == 8
    assert state.compute_rate == 30
    assert state.queue_length == 0


def test_environment_evolution_stays_in_plausible_range():
    env = DynamicEnvironment(DEFAULT_NODES, rng=random.Random(2))
    env.tick(steps=500)
    for state in env.states():
        assert state.network_latency_ms >= 0
        assert 0.3 <= state.load_factor <= 2.0


def test_environment_is_deterministic_with_same_seed():
    env_a = DynamicEnvironment(DEFAULT_NODES, rng=random.Random(9))
    env_b = DynamicEnvironment(DEFAULT_NODES, rng=random.Random(9))
    env_a.tick(steps=50)
    env_b.tick(steps=50)
    for name in ["local", "edge", "cloud"]:
        assert env_a.observe(name).network_latency_ms == env_b.observe(
            name
        ).network_latency_ms


def test_load_factor_reduces_effective_compute_rate():
    profile = DEFAULT_NODES[2]  # cloud, compute_rate 100
    state = NodeState.steady(profile)
    state.load_factor = 2.0
    assert state.compute_rate == 50


def test_queue_increases_latency_estimate():
    task = make_task(compute_units=100)
    state = NodeState.steady(DEFAULT_NODES[1])  # edge
    without_queue = estimate_latency_ms(task, state)
    state.queue_length = 4
    with_queue = estimate_latency_ms(task, state)
    assert with_queue > without_queue


def test_enqueue_dequeue():
    env = DynamicEnvironment(DEFAULT_NODES, rng=random.Random(3))
    env.enqueue("cloud")
    env.enqueue("cloud")
    assert env.observe("cloud").queue_length == 2
    env.dequeue("cloud")
    env.dequeue("cloud")
    env.dequeue("cloud")  # must not go negative
    assert env.observe("cloud").queue_length == 0


def test_overload_and_queue_raise_failure_probability():
    task = make_task()
    steady = NodeState.steady(DEFAULT_NODES[0])
    baseline_p = failure_probability(task, steady)

    overloaded = NodeState.steady(DEFAULT_NODES[0])
    overloaded.load_factor = 1.5
    overloaded.queue_length = 3
    assert failure_probability(task, overloaded) > baseline_p


def test_execution_uses_dynamic_state():
    task = make_task(compute_units=100)
    state = NodeState.steady(DEFAULT_NODES[1])
    state.network_latency_ms = 20
    state.load_factor = 2.0
    result = simulate_execution(task, state, rng=random.Random(5))
    assert result.network_latency_ms == 20
    # compute at half rate: 100 / 15 * 1.1 = 7.33ms
    assert result.compute_duration_ms > 6
    assert result.target == "edge"
