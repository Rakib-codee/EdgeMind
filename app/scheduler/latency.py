"""Latency estimation for scheduling decisions."""

from app.models.task import TaskRequest
from app.scheduler.nodes import NodeProfile


def estimate_latency_ms(task: TaskRequest, node: NodeProfile) -> float:
    """Estimated completion latency in milliseconds for a task on a node.

    Accepts either a static NodeProfile or a NodeState exposing
    network_latency_ms, compute_rate, and queue_length attributes.
    Queue wait assumes tasks ahead in the queue are of similar size.
    """
    queue_length = getattr(node, "queue_length", 0)
    service_ms = task.compute_units / node.compute_rate
    return node.network_latency_ms + service_ms * (1 + queue_length)
