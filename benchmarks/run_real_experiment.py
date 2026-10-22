"""Real-worker validation experiment runner.

Runs the baseline and adaptive scheduling policies — unchanged from the
simulation — against Dockerized CPU-bound workers (compose.real.yaml)
and records measured wall-clock outcomes.

Workload generation reuses benchmarks.run_benchmark.generate_tasks, so
both policies see identical task sequences within a run. Run order
alternates (AB/BA) across repetitions to reduce order effects.

Differences from the simulation, by design:
- Baseline selects from the static DEFAULT_NODES profiles (its defining
  behavior: no state observation), even though real worker rates differ.
- Adaptive observes real measured compute rates (from each worker's
  /state endpoint) but network latency is set to 0 because none is
  emulated, and queue_length is the scheduler's own count of submitted
  but not-yet-completed tasks, because bursts make polled worker state
  stale at decision time.
- Latency values here are measured wall-clock/perfcounter quantities,
  not simulated estimates.

Outputs: results/raw/real_experiment_v1.csv plus a provenance manifest.
"""

import argparse
import asyncio
import csv
import time
from pathlib import Path

import httpx

from app.models.task import TaskRequest
from app.scheduler import DEFAULT_NODES, select_target, select_target_adaptive
from app.scheduler.environment import NodeState
from app.scheduler.nodes import NodeProfile
from benchmarks.manifest import build_manifest, write_manifest
from benchmarks.run_benchmark import generate_tasks

DEFAULT_WORKERS = {
    "local": "http://localhost:8101",
    "edge": "http://localhost:8102",
    "cloud": "http://localhost:8103",
}

FIELDNAMES = [
    "run",
    "policy",
    "task_id",
    "compute_units",
    "max_latency_ms",
    "selected_target",
    "estimated_latency_ms",
    "rejected",
    "success",
    "deadline_met",
    "submit_ts",
    "response_ts",
    "e2e_latency_ms",
    "queue_wait_ms",
    "execution_ms",
    "scheduling_overhead_ms",
    "outstanding_at_submit",
    "error",
]


async def wait_for_workers(client: httpx.AsyncClient, workers: dict, timeout_s: float = 60.0) -> dict:
    """Block until every worker is healthy and calibrated; return rates."""
    deadline = time.monotonic() + timeout_s
    rates = {}
    while time.monotonic() < deadline:
        rates = {}
        for name, url in workers.items():
            try:
                state = (await client.get(f"{url}/state")).json()
                rates[name] = state["measured_compute_rate"]
            except (httpx.HTTPError, ValueError, KeyError):
                rates[name] = 0.0
        if all(r > 0 for r in rates.values()):
            return rates
        await asyncio.sleep(1.0)
    raise RuntimeError(f"workers not ready within {timeout_s}s: {rates}")


def build_adaptive_states(rates: dict, outstanding: dict) -> list[NodeState]:
    """Adaptive node view: measured rate, no emulated network latency,
    queue = tasks this scheduler has submitted but not yet completed."""
    return [
        NodeState(
            profile=NodeProfile(
                name=name, network_latency_ms=0.0, compute_rate=rates[name]
            ),
            network_latency_ms=0.0,
            queue_length=outstanding[name],
        )
        for name in rates
    ]


async def run_policy_once(
    policy: str,
    run_index: int,
    tasks: list[TaskRequest],
    workers: dict,
    rates: dict,
    client: httpx.AsyncClient,
) -> list[dict]:
    outstanding = {name: 0 for name in workers}
    rows = []

    async def execute(task: TaskRequest, target: str) -> dict:
        submit_ts = time.time()
        error = None
        try:
            resp = await client.post(
                f"{workers[target]}/execute",
                json=task.model_dump(),
                timeout=httpx.Timeout(300.0, connect=10.0),
            )
            resp.raise_for_status()
            body = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            body = {}
            error = f"{type(exc).__name__}: {exc}"
        response_ts = time.time()
        return {
            "submit_ts": round(submit_ts, 6),
            "response_ts": round(response_ts, 6),
            "e2e_latency_ms": round((response_ts - submit_ts) * 1000, 3),
            "queue_wait_ms": body.get("queue_wait_ms", ""),
            "execution_ms": body.get("execution_ms", ""),
            "success": bool(body.get("success", False)) and error is None,
            "error": error or body.get("error") or "",
        }

    pending = []
    for task in tasks:
        start = time.perf_counter_ns()
        if policy == "baseline":
            decision = select_target(task, DEFAULT_NODES)
        else:
            decision = select_target_adaptive(
                task, build_adaptive_states(rates, outstanding)
            )
        overhead_ms = (time.perf_counter_ns() - start) / 1e6

        row = {
            "run": run_index,
            "policy": policy,
            "task_id": task.task_id,
            "compute_units": task.compute_units,
            "max_latency_ms": task.max_latency_ms,
            "selected_target": "" if decision is None else decision.selected_target,
            "estimated_latency_ms": (
                "" if decision is None else decision.estimated_latency_ms
            ),
            "rejected": decision is None,
            "scheduling_overhead_ms": round(overhead_ms, 3),
            "outstanding_at_submit": "",
            "submit_ts": "",
            "response_ts": "",
            "e2e_latency_ms": "",
            "queue_wait_ms": "",
            "execution_ms": "",
            "success": False,
            "deadline_met": False,
            "error": "",
        }
        if decision is None:
            rows.append(row)
            continue

        target = decision.selected_target
        outstanding[target] += 1
        row["outstanding_at_submit"] = outstanding[target]

        async def tracked(t=task, tgt=target):
            try:
                return await execute(t, tgt)
            finally:
                outstanding[tgt] -= 1

        pending.append((row, asyncio.create_task(tracked())))
        rows.append(row)

    for row, fut in pending:
        result = await fut
        row.update(result)
        row["deadline_met"] = bool(
            result["success"]
            and result["e2e_latency_ms"] <= row["max_latency_ms"]
        )
    return rows


async def run_experiment(
    tasks: list[TaskRequest],
    workers: dict,
    runs: int,
) -> list[dict]:
    rows = []
    async with httpx.AsyncClient() as client:
        rates = await wait_for_workers(client, workers)
        print("measured worker rates (units/ms):", rates)
        for run_index in range(runs):
            # AB/BA alternation to reduce order effects.
            order = ("baseline", "adaptive") if run_index % 2 == 0 else ("adaptive", "baseline")
            for policy in order:
                rows.extend(
                    await run_policy_once(
                        policy, run_index, tasks, workers, rates, client
                    )
                )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Run real-worker experiment")
    parser.add_argument("--tasks", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument(
        "--budget-scale",
        type=float,
        default=1.0,
        help=(
            "Multiplier applied to every task's max_latency_ms. Workload "
            "budgets are calibrated to simulated node rates (10-100 "
            "units/ms); throttled containers are much slower, so a scale "
            "> 1 keeps deadlines feasible while staying identical across "
            "policies. Recorded in the manifest."
        ),
    )
    parser.add_argument("--out", type=Path, default=Path("results/raw/real_experiment_v1.csv"))
    parser.add_argument(
        "--worker",
        action="append",
        default=[],
        help="name=url override, repeatable (default: local/edge/cloud on :8101-8103)",
    )
    args = parser.parse_args()

    workers = dict(DEFAULT_WORKERS)
    for override in args.worker:
        name, url = override.split("=", 1)
        workers[name] = url

    tasks = generate_tasks(args.tasks, args.seed)
    if args.budget_scale != 1.0:
        tasks = [
            TaskRequest(
                task_id=t.task_id,
                compute_units=t.compute_units,
                max_latency_ms=round(t.max_latency_ms * args.budget_scale, 2),
            )
            for t in tasks
        ]
    rows = asyncio.run(run_experiment(tasks, workers, args.runs))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {args.out}")

    manifest = build_manifest(
        command=(
            f"python -m benchmarks.run_real_experiment --tasks {args.tasks} "
            f"--seed {args.seed} --runs {args.runs} "
            f"--budget-scale {args.budget_scale}"
        ),
        config={
            "tasks": args.tasks,
            "seed": args.seed,
            "runs": args.runs,
            "budget_scale": args.budget_scale,
            "workers": workers,
            "run_order": "AB/BA alternating",
            "network_latency": "not emulated (shared Docker bridge network)",
        },
        outputs=[args.out],
    )
    manifest_path = write_manifest(manifest, args.out.with_suffix(".manifest.json"))
    print(f"wrote manifest to {manifest_path}")


if __name__ == "__main__":
    main()
