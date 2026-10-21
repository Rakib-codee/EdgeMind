import random

from app.models.task import TaskRequest
from app.scheduler import (
    DEFAULT_NODES,
    DynamicEnvironment,
    NodeState,
    node_cost,
    select_target,
    select_target_adaptive,
)


def make_task(compute_units=100, max_latency_ms=5000, task_id="a1"):
    return TaskRequest(
        task_id=task_id,
        compute_units=compute_units,
        max_latency_ms=max_latency_ms,
    )


def steady_states():
    return [NodeState.steady(p) for p in DEFAULT_NODES]


def test_adaptive_selects_lowest_cost_node():
    task = make_task(compute_units=300)
    decision = select_target_adaptive(task, steady_states())
    # edge is fastest feasible in steady state, like baseline
    assert decision.selected_target == "edge"
    assert decision.scheduler == "adaptive"


def test_adaptive_avoids_overloaded_fast_node():
    task = make_task(compute_units=300)
    states = steady_states()
    edge = next(s for s in states if s.name == "edge")
    edge.load_factor = 2.0  # effective rate halves: 8 + 20 = 28ms
    edge.queue_length = 6
    decision = select_target_adaptive(task, states)
    assert decision.selected_target != "edge"


def test_baseline_ignores_overload_and_keeps_picking_edge():
    task = make_task(compute_units=300)
    states = steady_states()
    edge = next(s for s in states if s.name == "edge")
    edge.load_factor = 2.0
    edge.queue_length = 6
    # baseline works on static profiles, so it still picks edge
    decision = select_target(task, DEFAULT_NODES)
    assert decision.selected_target == "edge"


def test_cost_includes_latency_and_risk():
    task = make_task()
    states = steady_states()
    cloud = next(s for s in states if s.name == "cloud")
    cloud.load_factor = 1.8
    cloud.queue_length = 5
    penalized = node_cost(task, cloud)
    assert penalized > task.compute_units / cloud.compute_rate + 35


def test_adaptive_returns_none_when_all_infeasible():
    task = make_task(compute_units=100000, max_latency_ms=1)
    assert select_target_adaptive(task, steady_states()) is None


def test_adaptive_selection_is_deterministic():
    env_a = DynamicEnvironment(DEFAULT_NODES, rng=random.Random(11))
    env_b = DynamicEnvironment(DEFAULT_NODES, rng=random.Random(11))
    task = make_task(task_id="det")
    for _ in range(20):
        env_a.tick()
        env_b.tick()
    result_a = select_target_adaptive(task, env_a.states())
    result_b = select_target_adaptive(task, env_b.states())
    assert result_a == result_b
