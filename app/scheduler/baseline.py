"""Baseline scheduling policy.

Selects the feasible node with the lowest estimated latency.
Pure functions only — no I/O, no global state — so the policy is
directly unit-testable.
"""

from dataclasses import dataclass

from app.models.task import TaskRequest
from app.scheduler.latency import estimate_latency_ms
from app.scheduler.nodes import NodeProfile


@dataclass(frozen=True)
class SchedulingDecision:
    task_id: str
    selected_target: str
    estimated_latency_ms: float
    scheduler: str


def select_target(
    task: TaskRequest, nodes: tuple[NodeProfile, ...]
) -> SchedulingDecision | None:
    """Return the fastest feasible node, or None if none meets the deadline."""
    candidates = [
        (estimate_latency_ms(task, node), node.name) for node in nodes
    ]
    feasible = [
        (latency, name)
        for latency, name in candidates
        if latency <= task.max_latency_ms
    ]
    if not feasible:
        return None

    latency, name = min(feasible)
    return SchedulingDecision(
        task_id=task.task_id,
        selected_target=name,
        estimated_latency_ms=round(latency, 2),
        scheduler="baseline",
    )
