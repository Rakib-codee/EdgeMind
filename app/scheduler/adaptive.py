"""Adaptive scheduling policy.

Weighted, interpretable cost function over current node state:
estimated latency (including queue wait) + penalties for load and
failure risk. Among feasible nodes, the lowest cost wins.
"""

from dataclasses import dataclass

from app.models.task import TaskRequest
from app.scheduler.baseline import SchedulingDecision
from app.scheduler.environment import NodeState
from app.scheduler.latency import estimate_latency_ms
from app.workers.simulated_worker import failure_probability


@dataclass(frozen=True)
class AdaptiveWeights:
    # Extra latency-equivalent penalty per unit of load above nominal.
    load: float = 10.0
    # Extra latency-equivalent penalty per unit of failure probability.
    failure: float = 1000.0


DEFAULT_WEIGHTS = AdaptiveWeights()


def node_cost(
    task: TaskRequest,
    state: NodeState,
    weights: AdaptiveWeights = DEFAULT_WEIGHTS,
) -> float:
    """Cost of running a task on a node, in latency-equivalent ms."""
    latency = estimate_latency_ms(task, state)
    overload = max(0.0, state.load_factor - 1.0)
    risk = failure_probability(task, state)
    return latency + weights.load * overload + weights.failure * risk


def select_target_adaptive(
    task: TaskRequest,
    states: list[NodeState],
    weights: AdaptiveWeights = DEFAULT_WEIGHTS,
) -> SchedulingDecision | None:
    """Pick the feasible node with the lowest adaptive cost."""
    feasible = []
    for state in states:
        latency = estimate_latency_ms(task, state)
        if latency <= task.max_latency_ms:
            feasible.append((node_cost(task, state, weights), state.name, latency))

    if not feasible:
        return None

    cost, name, latency = min(feasible)
    return SchedulingDecision(
        task_id=task.task_id,
        selected_target=name,
        estimated_latency_ms=round(latency, 2),
        scheduler="adaptive",
    )
