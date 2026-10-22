"""Real-worker validation experiment runner (v2: fair comparison).

Runs four policies against Dockerized CPU-bound workers
(compose.real.yaml) and records measured wall-clock outcomes:

- A: original baseline — static assumed profiles (DEFAULT_NODES),
  no state observation. Historical Phase 3 configuration.
- B: calibrated baseline — the SAME baseline decision code path
  (select_target), but with per-run measured worker rates and zero
  (unemulated) network latency. No queue observation. Isolates the
  effect of rate calibration (B vs A).
- C: adaptive — measured rates, own outstanding-queue observation,
  queue-inclusive feasibility, frozen DEFAULT_WEIGHTS. (C vs B
  isolates queue awareness + failure-risk cost term.)
- D: exploratory ablation — adaptive with failure-weight 0. Runs last
  in every run under a fixed, documented order and is excluded from
  primary comparisons. Not tuned on evaluation results.

Fairness protocol (pre-registered in docs/real_worker_experiment.md):
- Within a run, all policies receive identical tasks (same seed).
- Run r uses workload seed = --seed + r (fresh range 500+, disjoint
  from all simulation seed ranges).
- A/B/C execution order follows a 6-permutation Latin square
  (run r -> permutation r % 6); D always last.
- Worker rates are recalibrated once per run via POST /calibrate,
  outside task measurement; queues fully drain between policy blocks,
  followed by a fixed cooldown.
- Scheduler weights are frozen; no tuning on these runs.

Outputs: results/raw/real_experiment_v2.csv plus a provenance manifest.
Phase 3 v1 outputs are never overwritten.
"""

import argparse
import asyncio
import csv
import itertools
import os
import subprocess
import time
from pathlib import Path

import httpx

from app.models.task import TaskRequest
from app.scheduler import DEFAULT_NODES, select_target, select_target_adaptive
from app.scheduler.adaptive import AdaptiveWeights, DEFAULT_WEIGHTS
from app.scheduler.environment import NodeState
from app.scheduler.nodes import NodeProfile
from benchmarks.manifest import build_manifest, write_manifest
from benchmarks.run_benchmark import generate_tasks

DEFAULT_WORKERS = {
    "local": "http://localhost:8101",
    "edge": "http://localhost:8102",
    "cloud": "http://localhost:8103",
}

PRIMARY_POLICIES = ("A", "B", "C")
EXPLORATORY_POLICIES = ("D",)
POLICY_LABELS = {
    "A": "baseline_static",
    "B": "baseline_calibrated",
    "C": "adaptive",
    "D": "adaptive_no_failure_risk",
}
# Exploratory ablation: adaptive cost without the failure-risk term.
NO_RISK_WEIGHTS = AdaptiveWeights(load=0.0, failure=0.0)

PERMUTATIONS = list(itertools.permutations(PRIMARY_POLICIES))

FIELDNAMES = [
    "run",
    "policy",
    "policy_label",
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
    "rate_local",
    "rate_edge",
    "rate_cloud",
    "load1_before",
    "load1_after",
]


def policy_order(run_index: int) -> tuple[str, ...]:
    """Deterministic counterbalanced order: Latin square over the six
    A/B/C permutations, with exploratory policy D always last."""
    primary = PERMUTATIONS[run_index % len(PERMUTATIONS)]
    return primary + EXPLORATORY_POLICIES


def decide(
    policy: str,
    task: TaskRequest,
    rates: dict,
    outstanding: dict,
):
    """Dispatch one scheduling decision through the policy's code path."""
    if policy == "A":
        return select_target(task, DEFAULT_NODES)
    if policy == "B":
        profiles = tuple(
            NodeProfile(name=name, network_latency_ms=0.0, compute_rate=rates[name])
            for name in rates
        )
        return select_target(task, profiles)
    states = build_adaptive_states(rates, outstanding)
    if policy == "C":
        return select_target_adaptive(task, states)
    if policy == "D":
        return select_target_adaptive(task, states, weights=NO_RISK_WEIGHTS)
    raise ValueError(f"unknown policy: {policy}")


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


async def recalibrate_workers(client: httpx.AsyncClient, workers: dict) -> dict:
    """Fresh per-run rate measurement, outside task measurement."""
    rates = {}
    for name, url in workers.items():
        resp = await client.post(f"{url}/calibrate", timeout=60.0)
        resp.raise_for_status()
        rates[name] = resp.json()["measured_compute_rate"]
    return rates


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
    run_meta: dict,
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
        decision = decide(policy, task, rates, outstanding)
        overhead_ms = (time.perf_counter_ns() - start) / 1e6

        row = {
            "run": run_index,
            "policy": policy,
            "policy_label": POLICY_LABELS[policy],
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
            **run_meta,
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


def host_load1() -> float | None:
    try:
        return round(os.getloadavg()[0], 2)
    except OSError:
        return None


def container_image_ids() -> dict:
    """Image IDs of the experiment workers; empty when unavailable."""
    try:
        out = subprocess.run(
            ["docker", "compose", "-f", "compose.real.yaml", "images", "-q"],
            capture_output=True, text=True, check=True,
        ).stdout.split()
        names = ("worker-local", "worker-edge", "worker-cloud")
        return {name: img[:19] for name, img in zip(names, out)}
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {}


async def run_experiment(
    seed: int,
    n_tasks: int,
    budget_scale: float,
    workers: dict,
    runs: int,
    cooldown_s: float,
) -> list[dict]:
    rows = []
    async with httpx.AsyncClient() as client:
        await wait_for_workers(client, workers)
        await asyncio.sleep(2.0)  # warm-up: settle after startup calibration
        for run_index in range(runs):
            rates = await recalibrate_workers(client, workers)
            run_meta = {
                **{f"rate_{name}": rates[name] for name in rates},
                "load1_before": host_load1(),
            }
            tasks = generate_tasks(n_tasks, seed + run_index)
            if budget_scale != 1.0:
                tasks = [
                    TaskRequest(
                        task_id=t.task_id,
                        compute_units=t.compute_units,
                        max_latency_ms=round(t.max_latency_ms * budget_scale, 2),
                    )
                    for t in tasks
                ]
            order = policy_order(run_index)
            print(f"run {run_index}: order={order} rates={rates}")
            for i, policy in enumerate(order):
                rows.extend(
                    await run_policy_once(
                        policy, run_index, tasks, workers, rates, client, run_meta
                    )
                )
                if i < len(order) - 1:
                    await asyncio.sleep(cooldown_s)
            for row in rows:
                if row["run"] == run_index:
                    row["load1_after"] = host_load1()
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Run real-worker experiment v2")
    parser.add_argument("--tasks", type=int, default=100)
    parser.add_argument("--seed", type=int, default=500,
                        help="base seed; run r uses seed+r (500-519 for 20 runs)")
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--cooldown", type=float, default=5.0,
                        help="seconds between policy blocks within a run")
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
    parser.add_argument("--out", type=Path, default=Path("results/raw/real_experiment_v2.csv"))
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

    rows = asyncio.run(
        run_experiment(
            args.seed, args.tasks, args.budget_scale, workers,
            args.runs, args.cooldown,
        )
    )

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
            "experiment": "real_experiment_v2",
            "tasks": args.tasks,
            "base_seed": args.seed,
            "runs": args.runs,
            "budget_scale": args.budget_scale,
            "cooldown_s": args.cooldown,
            "workers": workers,
            "policies": POLICY_LABELS,
            "primary_policies": list(PRIMARY_POLICIES),
            "exploratory_policies": list(EXPLORATORY_POLICIES),
            "order": "Latin square over 6 A/B/C permutations; D always last",
            "cpu_limits": {"local": 0.25, "edge": 0.5, "cloud": 1.0},
            "container_images": container_image_ids(),
            "network_latency": "not emulated (shared Docker bridge network)",
        },
        outputs=[args.out],
    )
    manifest_path = write_manifest(manifest, args.out.with_suffix(".manifest.json"))
    print(f"wrote manifest to {manifest_path}")


if __name__ == "__main__":
    main()
