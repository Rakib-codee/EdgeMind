"""Reproducible benchmark runner.

Runs baseline and adaptive policies against identical workloads and
identical DynamicEnvironment evolutions (same seeds), so comparisons
are fair. Writes one CSV row per task decision/execution.
"""

import argparse
import csv
import random
from pathlib import Path

from app.models.task import TaskRequest
from app.scheduler import (
    DEFAULT_NODES,
    DynamicEnvironment,
    select_target,
    select_target_adaptive,
)
from app.scheduler.adaptive import AdaptiveWeights
from app.workers.simulated_worker import simulate_execution

SIZE_CLASSES = {
    "small": (10, 100),
    "medium": (100, 1000),
    "large": (1000, 5000),
}
# Budget tightness: fraction of ideal local compute time used as the
# latency budget. Tight budgets create deadline pressure.
BUDGET_FACTORS = (0.5, 1.0, 2.0, 5.0)


def generate_tasks(count: int, seed: int) -> list[TaskRequest]:
    rng = random.Random(seed)
    tasks = []
    for i in range(count):
        size_name = rng.choice(list(SIZE_CLASSES))
        low, high = SIZE_CLASSES[size_name]
        compute = rng.uniform(low, high)
        ideal_local_ms = compute / 10  # local compute_rate = 10 units/ms
        budget = ideal_local_ms * rng.choice(BUDGET_FACTORS)
        tasks.append(
            TaskRequest(
                task_id=f"t{i:05d}",
                compute_units=round(compute, 2),
                max_latency_ms=round(budget, 2),
            )
        )
    return tasks


def run_policy(
    policy: str,
    tasks: list[TaskRequest],
    seed: int,
    weights: AdaptiveWeights | None = None,
) -> list[dict]:
    env = DynamicEnvironment(DEFAULT_NODES, rng=random.Random(seed))
    profile_by_name = {p.name: p for p in DEFAULT_NODES}
    rows = []

    for task in tasks:
        env.tick()
        _drain_queues(env)

        if policy == "baseline":
            decision = select_target(task, DEFAULT_NODES)
        elif policy == "adaptive":
            kwargs = {} if weights is None else {"weights": weights}
            decision = select_target_adaptive(task, env.states(), **kwargs)
        else:
            raise ValueError(f"unknown policy: {policy}")

        if decision is None:
            rows.append(
                {
                    "policy": policy,
                    "task_id": task.task_id,
                    "compute_units": task.compute_units,
                    "max_latency_ms": task.max_latency_ms,
                    "selected_target": "",
                    "rejected": True,
                    "success": False,
                    "deadline_met": False,
                    "network_latency_ms": "",
                    "compute_duration_ms": "",
                    "total_latency_ms": "",
                    "queue_length": "",
                    "load_factor": "",
                }
            )
            continue

        env.enqueue(decision.selected_target)
        if policy == "adaptive":
            node = env.observe(decision.selected_target)
        else:
            node = profile_by_name[decision.selected_target]
        result = simulate_execution(
            task, node, rng=random.Random(f"{seed}-{task.task_id}")
        )
        state = env.observe(decision.selected_target)

        rows.append(
            {
                "policy": policy,
                "task_id": task.task_id,
                "compute_units": task.compute_units,
                "max_latency_ms": task.max_latency_ms,
                "selected_target": result.target,
                "rejected": False,
                "success": result.success,
                "deadline_met": result.deadline_met,
                "network_latency_ms": result.network_latency_ms,
                "compute_duration_ms": result.compute_duration_ms,
                "total_latency_ms": result.total_latency_ms,
                "queue_length": state.queue_length,
                "load_factor": round(state.load_factor, 3),
            }
        )
    return rows


def _drain_queues(env: DynamicEnvironment) -> None:
    """Simulate queued tasks finishing: each queued task drains with p=0.3/tick."""
    for state in env.states():
        while state.queue_length > 0 and env.rng.random() < 0.3:
            env.dequeue(state.name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run EdgeMind benchmarks")
    parser.add_argument("--tasks", type=int, default=300)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    tasks = generate_tasks(args.tasks, args.seed)
    rows = []
    for policy in ("baseline", "adaptive"):
        rows.extend(run_policy(policy, tasks, args.seed))

    out = args.out or Path(f"results/raw/benchmark_seed{args.seed}.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
