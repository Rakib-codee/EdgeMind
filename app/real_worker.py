"""Real (non-simulated) CPU-bound worker service.

A minimal FastAPI service that executes deterministic CPU-bound work
(a SHA-256 hash chain whose length is proportional to the task's
compute_units) through a single-slot FIFO queue. Requests hold their
connection until the task completes; the response carries worker-side
timestamps so the experiment runner can separate queue wait from
execution time using measured wall-clock/perf-counter values.

This service is used only by the real-worker validation experiment
(benchmarks/run_real_experiment.py). It is intentionally separate from
the simulated worker and does not change any simulation semantics.

Environment variables:
    WORKER_NAME: logical node name (default "worker").
    ITERATIONS_PER_UNIT: hash iterations per compute unit (default 200).
"""

import asyncio
import hashlib
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from app.models.task import TaskRequest

WORKER_NAME = os.environ.get("WORKER_NAME", "worker")
ITERATIONS_PER_UNIT = int(os.environ.get("ITERATIONS_PER_UNIT", "200"))
# Workload used at startup to measure this worker's actual rate.
CALIBRATION_UNITS = 2000.0


def iterations_for(compute_units: float) -> int:
    """Map a task's compute units to a deterministic iteration count."""
    return max(1, round(compute_units * ITERATIONS_PER_UNIT))


def burn_cpu(iterations: int) -> str:
    """Deterministic CPU-bound work: iterated SHA-256 over a counter."""
    digest = b"edgemind-seed"
    for i in range(iterations):
        digest = hashlib.sha256(digest + i.to_bytes(8, "big")).digest()
    return digest.hex()


def calibrate_rate() -> float:
    """Measured compute rate in units/ms on this host/container."""
    iterations = iterations_for(CALIBRATION_UNITS)
    start = time.perf_counter_ns()
    burn_cpu(iterations)
    elapsed_ms = (time.perf_counter_ns() - start) / 1e6
    return CALIBRATION_UNITS / elapsed_ms


class ExecutionResponse(BaseModel):
    task_id: str
    worker: str
    success: bool
    # Unix wall-clock timestamps (seconds) at each lifecycle point.
    queued_at: float
    started_at: float
    finished_at: float
    # Durations from a monotonic clock, immune to wall-clock adjustments.
    queue_wait_ms: float
    execution_ms: float
    error: str | None = None


class WorkerState(BaseModel):
    worker: str
    queue_length: int
    in_flight: bool
    measured_compute_rate: float


class _WorkItem:
    __slots__ = ("task", "queued_wall", "queued_perf", "done", "result")

    def __init__(self, task: TaskRequest):
        self.task = task
        self.queued_wall = time.time()
        self.queued_perf = time.perf_counter_ns()
        self.done = asyncio.Event()
        self.result: ExecutionResponse | None = None


class _Worker:
    """Single-slot FIFO executor; one consumer task serializes work."""

    def __init__(self) -> None:
        self.queue: asyncio.Queue[_WorkItem] = asyncio.Queue()
        self.in_flight = False
        self.measured_rate = 0.0
        self._consumer: asyncio.Task | None = None

    async def start(self) -> None:
        self.measured_rate = await self.recalibrate()
        self._consumer = asyncio.create_task(self._consume())

    async def recalibrate(self) -> float:
        """(Re)measure this worker's compute rate; used at startup and
        once per experiment run so per-run rate drift is recorded."""
        self.measured_rate = await asyncio.to_thread(calibrate_rate)
        return self.measured_rate

    async def stop(self) -> None:
        if self._consumer is not None:
            self._consumer.cancel()

    async def submit(self, task: TaskRequest) -> ExecutionResponse:
        item = _WorkItem(task)
        await self.queue.put(item)
        await item.done.wait()
        assert item.result is not None
        return item.result

    async def _consume(self) -> None:
        while True:
            item = await self.queue.get()
            self.in_flight = True
            started_wall = time.time()
            started_perf = time.perf_counter_ns()
            error = None
            try:
                await asyncio.to_thread(
                    burn_cpu, iterations_for(item.task.compute_units)
                )
            except Exception as exc:  # pragma: no cover - defensive
                error = f"{type(exc).__name__}: {exc}"
            finished_wall = time.time()
            finished_perf = time.perf_counter_ns()
            self.in_flight = False
            item.result = ExecutionResponse(
                task_id=item.task.task_id,
                worker=WORKER_NAME,
                success=error is None,
                queued_at=item.queued_wall,
                started_at=started_wall,
                finished_at=finished_wall,
                queue_wait_ms=(started_perf - item.queued_perf) / 1e6,
                execution_ms=(finished_perf - started_perf) / 1e6,
                error=error,
            )
            item.done.set()


_worker = _Worker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _worker.start()
    yield
    await _worker.stop()


app = FastAPI(title="EdgeMind Real Worker", lifespan=lifespan)


@app.post("/execute", response_model=ExecutionResponse)
async def execute(task: TaskRequest) -> ExecutionResponse:
    return await _worker.submit(task)


@app.get("/state", response_model=WorkerState)
async def state() -> WorkerState:
    return WorkerState(
        worker=WORKER_NAME,
        queue_length=_worker.queue.qsize(),
        in_flight=_worker.in_flight,
        measured_compute_rate=round(_worker.measured_rate, 4),
    )


@app.post("/calibrate", response_model=WorkerState)
async def calibrate() -> WorkerState:
    """Re-run rate calibration on demand (experiment runner calls this
    once per run, outside task measurement). Refuses while busy so
    calibration never overlaps measured task execution."""
    if _worker.in_flight or _worker.queue.qsize() > 0:
        from fastapi import HTTPException

        raise HTTPException(status_code=409, detail="worker busy")
    await _worker.recalibrate()
    return await state()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "worker": WORKER_NAME}
