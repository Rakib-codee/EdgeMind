"""Research evaluation runner (Phase 11).

Runs baseline, adaptive, and ablated adaptive policies across multiple
seeds. Every policy sees identical task workloads and identical
DynamicEnvironment evolutions per seed, enabling paired comparison.

Outputs a single combined CSV with a `seed` column for analysis.
"""

import argparse
import csv
from pathlib import Path

from app.scheduler.adaptive import AdaptiveWeights
from benchmarks.run_benchmark import generate_tasks, run_policy

# Ablated adaptive variants: each disables one cost component to show
# its individual contribution.
POLICY_VARIANTS = {
    "baseline": None,
    "adaptive": AdaptiveWeights(),
    "adaptive_no_load": AdaptiveWeights(load=0.0),
    "adaptive_no_failure": AdaptiveWeights(failure=0.0),
    "adaptive_latency_only": AdaptiveWeights(load=0.0, failure=0.0),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run research evaluation")
    parser.add_argument("--tasks", type=int, default=300)
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--first-seed", type=int, default=42)
    parser.add_argument(
        "--out", type=Path, default=Path("results/raw/evaluation.csv")
    )
    args = parser.parse_args()

    rows = []
    for seed in range(args.first_seed, args.first_seed + args.seeds):
        tasks = generate_tasks(args.tasks, seed)
        for name, weights in POLICY_VARIANTS.items():
            policy = "adaptive" if name.startswith("adaptive") else name
            for row in run_policy(policy, tasks, seed, weights):
                row["variant"] = name
                row["seed"] = seed
                rows.append(row)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
