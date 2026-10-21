"""Simulated worker execution.

Runs tasks against simulated node profiles. Durations are computed
mathematically (no real sleeping), so experiments stay fast and
reproducible. Runtime variation is drawn from a seedable RNG.
"""

import random

from app.models.task import TaskRequest, TaskResult
from app.scheduler.environment import NodeState
from app.scheduler.nodes import NodeProfile

# Multiplier applied to ideal compute time to model real-world runtime
# variance and overhead on a simulated node.
RUNTIME_OVERHEAD_FACTOR = 1.1
JITTER_FRACTION = 0.05


def simulate_execution(
    task: TaskRequest,
    node: NodeProfile | NodeState,
    rng: random.Random | None = None,
) -> TaskResult:
    """Simulate running a task on a node and return the outcome."""
    rng = rng or random.Random(task.task_id)

    compute_duration = (
        task.compute_units / node.compute_rate
    ) * RUNTIME_OVERHEAD_FACTOR
    jitter = compute_duration * JITTER_FRACTION * rng.uniform(-1, 1)
    compute_duration = max(0.0, compute_duration + jitter)

    total_latency = node.network_latency_ms + compute_duration
    success = rng.random() > failure_probability(task, node)

    return TaskResult(
        task_id=task.task_id,
        target=node.name,
        success=success,
        network_latency_ms=round(node.network_latency_ms, 2),
        compute_duration_ms=round(compute_duration, 2),
        total_latency_ms=round(total_latency, 2),
        deadline_met=total_latency <= task.max_latency_ms,
    )


def failure_probability(task: TaskRequest, node: NodeProfile | NodeState) -> float:
    """Probability of task failure: base drop rate plus overload effects."""
    probability = 0.01
    load = getattr(node, "load_factor", 1.0)
    queue = getattr(node, "queue_length", 0)
    probability += 0.05 * max(0.0, load - 1.0)
    probability += 0.02 * queue
    return min(probability, 0.5)
