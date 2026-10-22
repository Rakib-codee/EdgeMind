"""Weight tuning for the adaptive policy (Phase 3, v2).

Grid-searches AdaptiveWeights on dedicated *tuning* seeds (distinct
from the held-out evaluation seeds) to avoid overfitting the final
report. Selection criterion: highest overall on-time completion rate
(successful and within deadline, over ALL submitted tasks), tie-broken
by mean latency. This objective covers both admission and execution
quality, so the admission trade-off is part of tuning.

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
    ontime = sum(r["success"] and r["deadline_met"] for r in completed)
    return {
        "tasks": len(rows),
        "rejection_rate": round(1 - len(completed) / len(rows), 4),
        "accepted_deadline_miss_rate": round(
            1 - sum(r["deadline_met"] for r in completed) / len(completed), 4
        ),
        "accepted_success_rate": round(
            sum(r["success"] for r in completed) / len(completed), 4
        ),
        "overall_ontime_rate": round(ontime / len(rows), 4),
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
            all_rows = []
            for seed in range(args.first_seed, args.first_seed + args.seeds):
                tasks = generate_tasks(args.tasks, seed)
                all_rows.extend(run_policy("adaptive", tasks, seed, weights))
            summary = summarize(all_rows)
            rows.append({"w_load": w_load, "w_failure": w_failure, **summary})

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    best = max(
        rows, key=lambda r: (r["overall_ontime_rate"], -r["latency_mean_ms"])
    )
    for r in sorted(rows, key=lambda r: r["overall_ontime_rate"], reverse=True):
        print(r)
    print(f"\nbest config: {best}")
    print(f"wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
