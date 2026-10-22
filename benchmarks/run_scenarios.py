"""Scenario benchmarks (Phase 5).

Compares baseline and adaptive policies across workload intensity and
network-latency regimes on held-out seeds, so the tuned weights are
evaluated on data not used during tuning.

Scenarios:
- moderate: 300 tasks, default network latency
- light: 150 tasks (queues rarely build up)
- heavy: 600 tasks (queue buildup and overload)
- low_latency_net: network latencies halved
- high_latency_net: network latencies doubled
"""

import argparse
import csv
from pathlib import Path

from app.scheduler.nodes import DEFAULT_NODES, NodeProfile
from benchmarks.manifest import build_manifest, write_manifest
from benchmarks.run_benchmark import generate_tasks, run_policy

HELD_OUT_FIRST_SEED = 100

SCENARIOS = {
    "moderate": {"tasks": 300, "latency_scale": 1.0},
    "light": {"tasks": 150, "latency_scale": 1.0},
    "heavy": {"tasks": 600, "latency_scale": 1.0},
    "low_latency_net": {"tasks": 300, "latency_scale": 0.5},
    "high_latency_net": {"tasks": 300, "latency_scale": 2.0},
}


def scaled_nodes(latency_scale: float) -> tuple[NodeProfile, ...]:
    return tuple(
        NodeProfile(
            name=p.name,
            network_latency_ms=p.network_latency_ms * latency_scale,
            compute_rate=p.compute_rate,
        )
        for p in DEFAULT_NODES
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run scenario benchmarks")
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument(
        "--first-seed", type=int, default=HELD_OUT_FIRST_SEED,
        help="held-out seeds not used for weight tuning",
    )
    parser.add_argument(
        "--out", type=Path, default=Path("results/raw/scenarios.csv")
    )
    args = parser.parse_args()

    rows = []
    for scenario, cfg in SCENARIOS.items():
        nodes = scaled_nodes(cfg["latency_scale"])
        for seed in range(args.first_seed, args.first_seed + args.seeds):
            tasks = generate_tasks(cfg["tasks"], seed)
            for policy in ("baseline", "adaptive"):
                for row in run_policy(policy, tasks, seed, nodes=nodes):
                    row["scenario"] = scenario
                    row["seed"] = seed
                    rows.append(row)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {args.out}")

    manifest_path = write_manifest(
        build_manifest(
            command=(
                "python -m benchmarks.run_scenarios "
                f"--seeds {args.seeds} --first-seed {args.first_seed} "
                f"--out {args.out}"
            ),
            config={
                "first_seed": args.first_seed,
                "seeds": args.seeds,
                "scenarios": SCENARIOS,
                "policies": ["baseline", "adaptive"],
            },
            outputs=[args.out],
        ),
        args.out.with_suffix(".manifest.json"),
    )
    print(f"wrote manifest to {manifest_path}")


if __name__ == "__main__":
    main()
