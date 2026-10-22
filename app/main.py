import os
import random

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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

# CORS for the browser-based demo UI. Origins are configurable so the
# deployed frontend (Vercel) can be allowed without opening the API to
# every origin in production-like use.
ALLOWED_ORIGINS = os.environ.get(
    "EDGEMIND_CORS_ORIGINS", "http://localhost:5173,http://localhost:4173"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
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


@app.get("/state")
def environment_state():
    """Current simulated node states (drives the demo UI's node cards)."""
    return [
        {
            "name": s.name,
            "network_latency_ms": round(s.network_latency_ms, 2),
            "compute_rate": round(s.compute_rate, 2),
            "load_factor": round(s.load_factor, 3),
            "queue_length": s.queue_length,
        }
        for s in ENV.states()
    ]


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


@app.post("/benchmark")
def run_benchmark(tasks: int = 100, seed: int = 42):
    """Run a paired mini-benchmark (baseline vs adaptive) on demand.

    Deterministic for a given seed; powers the Experiment Control Panel
    in the demo UI. Uses the same workload generator and policies as the
    research pipeline, but runs in isolation from the live ENV.
    """
    from benchmarks.run_benchmark import generate_tasks, run_policy

    if not (10 <= tasks <= 500):
        raise HTTPException(status_code=400, detail="tasks must be 10-500")
    if not (0 <= seed <= 999_999):
        raise HTTPException(status_code=400, detail="seed must be 0-999999")

    workload = generate_tasks(tasks, seed)
    out = {}
    for policy in ("baseline", "adaptive"):
        rows = run_policy(policy, workload, seed)
        accepted = [r for r in rows if not r["rejected"]]
        successful = [r for r in accepted if r["success"]]
        on_time = [r for r in successful if r["deadline_met"]]
        latencies = sorted(float(r["total_latency_ms"]) for r in successful)
        p95 = latencies[int(0.95 * (len(latencies) - 1))] if latencies else None
        out[policy] = {
            "submitted": len(rows),
            "rejected": len(rows) - len(accepted),
            "successful": len(successful),
            "on_time": len(on_time),
            "overall_on_time_rate": round(len(on_time) / len(rows), 4),
            "completed_miss_rate": (
                round(1 - len(on_time) / len(successful), 4) if successful else None
            ),
            "latency_mean_ms": (
                round(sum(latencies) / len(latencies), 2) if latencies else None
            ),
            "latency_p95_ms": round(p95, 2) if p95 is not None else None,
        }
    return {"tasks": tasks, "seed": seed, "policies": out}
