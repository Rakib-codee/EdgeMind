"""Weight tuning for the adaptive policy (Phase 3).

Grid-searches AdaptiveWeights on dedicated *tuning* seeds (distinct
from the held-out evaluation seeds) to avoid overfitting the final
report. Selection criterion: lowest deadline-miss rate, tie-broken by
mean latency.

Writes a CSV with one row per weight configuration.
"""

import argparse
import csv
from pathlib import Path

from app.scheduler.adaptive import AdaptiveWeights
from benchmarks.run_benchmark import generate_tasks, run_policy

# Candidate grid. w_failure=1000 is the previous default; the ablation
# in Phase 11 suggested it is too aggressive.
GRID = {
    "load": (0.0, 5.0, 10.0, 20.0),
    "failure": (0.0, 200.0, 500.0, 1000.0),
}


def summarize(rows: list[dict]) -> dict:
    completed = [r for r in rows if not r["rejected"]]
    latency = [r["total_latency_ms"] for r in completed]
    return {
        "tasks": len(rows),
        "deadline_miss_rate": round(
            1 - sum(r["deadline_met"] for r in completed) / len(completed), 4
        ),
        "success_rate": round(
            sum(r["success"] for r in completed) / len(completed), 4
        ),
        "latency_mean_ms": round(sum(latency) / len(latency), 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Tune adaptive weights")
    parser.add_argument("--tasks", type=int, default=300)
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--first-seed", type=int, default=42)
    parser.add_argument(
        "--out", type=Path, default=Path("results/raw/weight_tuning.csv")
    )
    args = parser.parse_args()

    rows = []
    for w_load in GRID["load"]:
        for w_failure in GRID["failure"]:
            weights = AdaptiveWeights(load=w_load, failure=w_failure)
            aggregate = {"tasks": 0, "misses": 0, "successes": 0,
                         "latency_sum": 0.0, "completed": 0}
            for seed in range(args.first_seed, args.first_seed + args.seeds):
                tasks = generate_tasks(args.tasks, seed)
                for r in run_policy("adaptive", tasks, seed, weights):
                    aggregate["tasks"] += 1
                    if r["rejected"]:
                        continue
                    aggregate["completed"] += 1
                    aggregate["misses"] += not r["deadline_met"]
                    aggregate["successes"] += r["success"]
                    aggregate["latency_sum"] += r["total_latency_ms"]
            rows.append(
                {
                    "w_load": w_load,
                    "w_failure": w_failure,
                    "tasks": aggregate["tasks"],
                    "deadline_miss_rate": round(
                        aggregate["misses"] / aggregate["completed"], 4
                    ),
                    "success_rate": round(
                        aggregate["successes"] / aggregate["completed"], 4
                    ),
                    "latency_mean_ms": round(
                        aggregate["latency_sum"] / aggregate["completed"], 2
                    ),
                }
            )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    best = min(rows, key=lambda r: (r["deadline_miss_rate"], r["latency_mean_ms"]))
    for r in sorted(rows, key=lambda r: r["deadline_miss_rate"]):
        print(r)
    print(f"\nbest config: {best}")
    print(f"wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
