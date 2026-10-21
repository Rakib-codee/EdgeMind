
import random

from fastapi import FastAPI, HTTPException

from app.models.task import TaskRequest
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


def get_node(name: str):
    return next((n for n in NODES if n.name == name), None)


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


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "EdgeMind"}


@app.post("/schedule")
def schedule_task(task: TaskRequest, policy: str = "baseline"):
    decision = schedule(task, policy)
    if decision is None:
        raise HTTPException(
            status_code=422,
            detail="No execution target meets the latency limit.",
        )
    return {
        "task_id": decision.task_id,
        "selected_target": decision.selected_target,
        "estimated_latency_ms": decision.estimated_latency_ms,
        "scheduler": decision.scheduler,
    }


@app.post("/execute")
def execute_task(task: TaskRequest, policy: str = "baseline"):
    """Schedule a task, then simulate its execution end to end."""
    decision = schedule(task, policy)
    if decision is None:
        raise HTTPException(
            status_code=422,
            detail="No execution target meets the latency limit.",
        )
    node = get_node(decision.selected_target)
    if policy == "adaptive":
        node = ENV.observe(decision.selected_target)
        ENV.enqueue(decision.selected_target)
    result = simulate_execution(task, node)
    return result.model_dump()
