
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="EdgeMind",
    description="Intelligent Edge-Cloud Workload Orchestrator",
    version="0.1.0",
)


class TaskRequest(BaseModel):
    task_id: str
    compute_units: float = Field(gt=0)
    max_latency_ms: float = Field(gt=0)


# Initial simulated node profiles.
# These are assumptions for development, not measured hardware results.
NODES = [
    {
        "name": "local",
        "network_latency_ms": 0,
        "compute_rate": 10,
    },
    {
        "name": "edge",
        "network_latency_ms": 8,
        "compute_rate": 30,
    },
    {
        "name": "cloud",
        "network_latency_ms": 35,
        "compute_rate": 100,
    },
]


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "EdgeMind"}


@app.post("/schedule")
def schedule_task(task: TaskRequest):
    candidates = []

    for node in NODES:
        estimated_latency = (
            node["network_latency_ms"]
            + task.compute_units / node["compute_rate"]
        )

        if estimated_latency <= task.max_latency_ms:
            candidates.append(
                {
                    "target": node["name"],
                    "estimated_latency_ms": round(
                        estimated_latency, 2
                    ),
                }
            )

    if not candidates:
        raise HTTPException(
            status_code=422,
            detail="No execution target meets the latency limit.",
        )

    best = min(
        candidates,
        key=lambda candidate: candidate["estimated_latency_ms"],
    )

    return {
        "task_id": task.task_id,
        "selected_target": best["target"],
        "estimated_latency_ms": best["estimated_latency_ms"],
        "scheduler": "baseline",
    }
