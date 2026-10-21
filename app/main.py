
from fastapi import FastAPI, HTTPException

from app.models.task import TaskRequest
from app.scheduler import DEFAULT_NODES, select_target

app = FastAPI(
    title="EdgeMind",
    description="Intelligent Edge-Cloud Workload Orchestrator",
    version="0.1.0",
)

# Initial simulated node profiles.
# These are assumptions for development, not measured hardware results.
NODES = DEFAULT_NODES


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "EdgeMind"}


@app.post("/schedule")
def schedule_task(task: TaskRequest):
    decision = select_target(task, NODES)
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
