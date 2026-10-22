
import random

from fastapi import FastAPI, HTTPException
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from app.models.task import TaskRequest
from app.monitoring import metrics
from app.scheduler import (
    DEFAULT_NODES,
    DynamicEnvironment,
    select_target,
    select_target_adaptive,
)
from app.workers.simulated_worker import simulate_execution

app = FastAPI(
    title="EdgeMind",
    description="Intelligent Edge-Cloud Workload Orchestrator",
    version="0.1.0",
)

# Initial simulated node profiles.
# These are assumptions for development, not measured hardware results.
NODES = DEFAULT_NODES
ENV = DynamicEnvironment(DEFAULT_NODES, rng=random.Random(42))


def schedule(task: TaskRequest, policy: str):
    if policy == "baseline":
        return select_target(task, NODES)
    if policy == "adaptive":
        ENV.tick()
        return select_target_adaptive(task, ENV.states())
    raise HTTPException(
        status_code=400,
        detail=f"Unknown policy '{policy}'. Use 'baseline' or 'adaptive'.",
    )


def schedule_or_fail(task: TaskRequest, policy: str):
    decision = schedule(task, policy)
    if decision is None:
        metrics.SCHEDULE_FAILURES.labels(policy=policy).inc()
        raise HTTPException(
            status_code=422,
            detail="No execution target meets the latency limit.",
        )
    metrics.TASKS_SCHEDULED.labels(
        policy=policy, target=decision.selected_target
    ).inc()
    return decision


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "EdgeMind"}


@app.get("/metrics")
def prometheus_metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/schedule")
def schedule_task(task: TaskRequest, policy: str = "baseline"):
    decision = schedule_or_fail(task, policy)
    return {
        "task_id": decision.task_id,
        "selected_target": decision.selected_target,
        "estimated_latency_ms": decision.estimated_latency_ms,
        "scheduler": decision.scheduler,
    }


@app.post("/execute")
def execute_task(task: TaskRequest, policy: str = "baseline"):
    """Schedule a task, then simulate its execution end to end.

    Both policies execute against the observed dynamic node state so
    comparisons stay fair; the task enqueues after execution so it does
    not count itself as queue wait.
    """
    decision = schedule_or_fail(task, policy)
    node = ENV.observe(decision.selected_target)
    result = simulate_execution(task, node)
    metrics.record_execution(result)
    ENV.enqueue(decision.selected_target)
    return result.model_dump()
