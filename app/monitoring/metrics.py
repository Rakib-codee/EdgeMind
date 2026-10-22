"""Prometheus metric definitions.

Metrics track scheduling decisions and simulated task execution
outcomes so runtime behaviour can be observed on a dashboard.
"""

from prometheus_client import Counter, Histogram

TASKS_SCHEDULED = Counter(
    "edgemind_tasks_scheduled_total",
    "Tasks for which a target was selected",
    ["policy", "target"],
)

SCHEDULE_FAILURES = Counter(
    "edgemind_schedule_failures_total",
    "Tasks with no feasible execution target",
    ["policy"],
)

TASKS_EXECUTED = Counter(
    "edgemind_tasks_executed_total",
    "Simulated task executions by outcome",
    ["target", "status"],
)

TASK_LATENCY = Histogram(
    "edgemind_task_latency_ms",
    "Total simulated task latency in milliseconds",
    ["target"],
    buckets=(5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000),
)

COMPUTE_DURATION = Histogram(
    "edgemind_task_compute_duration_ms",
    "Simulated compute duration in milliseconds",
    ["target"],
    buckets=(1, 5, 10, 25, 50, 100, 250, 500, 1000),
)


def record_execution(result) -> None:
    """Update execution metrics from a TaskResult."""
    status = "success" if result.success else "failed"
    TASKS_EXECUTED.labels(target=result.target, status=status).inc()
    TASK_LATENCY.labels(target=result.target).observe(result.total_latency_ms)
    COMPUTE_DURATION.labels(target=result.target).observe(
        result.compute_duration_ms
    )
