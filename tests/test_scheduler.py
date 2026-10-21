from app.models.task import TaskRequest
from app.scheduler import DEFAULT_NODES, estimate_latency_ms, select_target
from app.scheduler.baseline import SchedulingDecision


def make_task(compute_units=100, max_latency_ms=5000, task_id="t1"):
    return TaskRequest(
        task_id=task_id,
        compute_units=compute_units,
        max_latency_ms=max_latency_ms,
    )


def test_latency_estimation_is_network_plus_compute():
    task = make_task(compute_units=100)
    local = next(n for n in DEFAULT_NODES if n.name == "local")
    edge = next(n for n in DEFAULT_NODES if n.name == "edge")
    assert estimate_latency_ms(task, local) == 10.0
    assert estimate_latency_ms(task, edge) == 8 + 100 / 30


def test_select_target_picks_fastest_feasible_node():
    task = make_task(compute_units=300, max_latency_ms=5000)
    decision = select_target(task, DEFAULT_NODES)
    assert isinstance(decision, SchedulingDecision)
    # edge: 8 + 10 = 18ms beats local: 30ms and cloud: 38ms
    assert decision.selected_target == "edge"
    assert decision.estimated_latency_ms == 18.0
    assert decision.scheduler == "baseline"


def test_select_target_returns_none_when_infeasible():
    task = make_task(compute_units=100000, max_latency_ms=1)
    assert select_target(task, DEFAULT_NODES) is None


def test_select_target_respects_latency_budget():
    task = make_task(compute_units=120, max_latency_ms=12)
    decision = select_target(task, DEFAULT_NODES)
    # local: 12ms feasible, edge: 8 + 4 feasible, cloud: 35 + 1.2 infeasible
    assert decision is not None
    assert decision.selected_target == "edge"
    assert decision.estimated_latency_ms <= 12
