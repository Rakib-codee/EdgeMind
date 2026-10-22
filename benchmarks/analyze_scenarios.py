"""Analyze scenario benchmark results (Phase 5).

Per scenario: headline metrics per policy and the paired
adaptive - baseline difference with bootstrap 95% CI across seeds.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

BOOTSTRAP_SEED = 20241022
BOOTSTRAP_RESAMPLES = 10000


def scenario_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Per (scenario, seed, policy): accepted-task metrics plus
    rejection-aware overall metrics (population: all submitted tasks)."""
    rows = []
    for (scenario, seed, policy), group in df.groupby(
        ["scenario", "seed", "policy"]
    ):
        completed = group[~group["rejected"]]
        latency = pd.to_numeric(completed["total_latency_ms"], errors="coerce")
        ontime = (completed["success"] & completed["deadline_met"]).sum()
        rows.append(
            {
                "scenario": scenario,
                "seed": seed,
                "policy": policy,
                "tasks": len(group),
                "rejected": int(group["rejected"].sum()),
                "rejection_rate": round(group["rejected"].mean(), 4),
                "accepted_success_rate": round(completed["success"].mean(), 4),
                "accepted_deadline_miss_rate": round(
                    1 - completed["deadline_met"].mean(), 4
                ),
                "overall_ontime_rate": round(ontime / len(group), 4),
                "overall_success_rate": round(
                    completed["success"].sum() / len(group), 4
                ),
                "latency_mean_ms": round(latency.mean(), 2),
                "latency_p95_ms": round(latency.quantile(0.95), 2),
                "latency_p99_ms": round(latency.quantile(0.99), 2),
            }
        )
    return pd.DataFrame(rows)


def paired_by_scenario(summary: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    rows = []
    for scenario, group in summary.groupby("scenario"):
        pivot = group.pivot(index="seed", columns="policy")
        for metric in (
            "accepted_deadline_miss_rate",
            "accepted_success_rate",
            "rejection_rate",
            "overall_ontime_rate",
            "latency_mean_ms",
            "latency_p95_ms",
        ):
            diff = (
                pivot[(metric, "adaptive")] - pivot[(metric, "baseline")]
            ).to_numpy()
            means = rng.choice(
                diff, size=(BOOTSTRAP_RESAMPLES, len(diff))
            ).mean(axis=1)
            rows.append(
                {
                    "scenario": scenario,
                    "metric": metric,
                    "mean_diff": round(float(diff.mean()), 4),
                    "ci95_low": round(float(np.percentile(means, 2.5)), 4),
                    "ci95_high": round(float(np.percentile(means, 97.5)), 4),
                    "n_seeds": len(diff),
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze scenario results")
    parser.add_argument("input", type=Path, help="scenario CSV")
    parser.add_argument(
        "--out-dir", type=Path, default=Path("results/processed")
    )
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    summary = scenario_summary(df)
    summary.to_csv(args.out_dir / "scenario_per_seed.csv", index=False)

    paired = paired_by_scenario(summary)
    paired.to_csv(args.out_dir / "scenario_paired.csv", index=False)
    print("Paired comparison per scenario (adaptive - baseline):")
    print(paired.to_string(index=False))
    print(f"\nwrote {args.out_dir / 'scenario_per_seed.csv'}")
    print(f"wrote {args.out_dir / 'scenario_paired.csv'}")


if __name__ == "__main__":
    main()
