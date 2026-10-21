"""Latency estimation for scheduling decisions."""

from app.scheduler.nodes import NodeProfile
from app.models.task import TaskRequest


def estimate_latency_ms(task: TaskRequest, node: NodeProfile) -> float:
    """Estimated completion latency in milliseconds for a task on a node."""
    return node.network_latency_ms + task.compute_units / node.compute_rate
