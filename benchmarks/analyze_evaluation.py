"""Research evaluation analysis (Phase 11).

Reads the combined evaluation CSV and produces:
- per-seed, per-variant summary statistics
- paired comparison of adaptive vs baseline with bootstrap 95% CI
- ablation contribution table
- sensitivity analysis by latency-budget tightness
- comparison plots
"""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Deterministic bootstrap for confidence intervals.
BOOTSTRAP_SEED = 20241022
BOOTSTRAP_RESAMPLES = 10000

BASELINE = "baseline"
FULL_ADAPTIVE = "adaptive"


def per_run_summary(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (seed, variant) with headline metrics."""
    rows = []
    for (seed, variant), group in df.groupby(["seed", "variant"]):
        completed = group[~group["rejected"]]
        latency = pd.to_numeric(completed["total_latency_ms"], errors="coerce")
        rows.append(
            {
                "seed": seed,
                "variant": variant,
                "tasks": len(group),
                "scheduled": len(completed),
                "rejected": int(group["rejected"].sum()),
                "success_rate": round(completed["success"].mean(), 4),
                "deadline_miss_rate": round(
                    1 - completed["deadline_met"].mean(), 4
                ),
                "latency_mean_ms": round(latency.mean(), 2),
                "latency_median_ms": round(latency.median(), 2),
                "latency_p95_ms": round(latency.quantile(0.95), 2),
            }
        )
    return pd.DataFrame(rows)


def paired_comparison(summary: pd.DataFrame) -> pd.DataFrame:
    """Paired per-seed difference (adaptive - baseline) with bootstrap CI.

    Negative differences mean adaptive is better (lower latency / miss rate).
    """
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    rows = []
    for metric in ("latency_mean_ms", "deadline_miss_rate", "success_rate"):
        pivot = summary.pivot(index="seed", columns="variant", values=metric)
        diff = (pivot[FULL_ADAPTIVE] - pivot[BASELINE]).to_numpy()
        means = rng.choice(diff, size=(BOOTSTRAP_RESAMPLES, len(diff))).mean(axis=1)
        rows.append(
            {
                "metric": metric,
                "mean_diff": round(float(diff.mean()), 4),
                "ci95_low": round(float(np.percentile(means, 2.5)), 4),
                "ci95_high": round(float(np.percentile(means, 97.5)), 4),
                "n_seeds": len(diff),
            }
        )
    return pd.DataFrame(rows)


def ablation_table(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate metrics per variant across all seeds."""
    rows = []
    for variant, group in df.groupby("variant"):
        completed = group[~group["rejected"]]
        latency = pd.to_numeric(completed["total_latency_ms"], errors="coerce")
        rows.append(
            {
                "variant": variant,
                "deadline_miss_rate": round(
                    1 - completed["deadline_met"].mean(), 4
                ),
                "success_rate": round(completed["success"].mean(), 4),
                "latency_mean_ms": round(latency.mean(), 2),
                "latency_p95_ms": round(latency.quantile(0.95), 2),
            }
        )
    return pd.DataFrame(rows).sort_values("deadline_miss_rate")


def sensitivity_table(df: pd.DataFrame) -> pd.DataFrame:
    """Metrics split by latency-budget tightness.

    Budget tightness = max_latency_ms / ideal local compute time.
    Tight (< 1) means the budget is below ideal local execution time.
    """
    rows = []
    work = df.copy()
    work["ideal_local_ms"] = work["compute_units"] / 10.0
    work["tightness"] = work["max_latency_ms"] / work["ideal_local_ms"]
    work["regime"] = np.where(work["tightness"] < 1.0, "tight", "loose")
    for (variant, regime), group in work.groupby(["variant", "regime"]):
        completed = group[~group["rejected"]]
        rows.append(
            {
                "variant": variant,
                "regime": regime,
                "tasks": len(group),
                "deadline_miss_rate": round(
                    1 - completed["deadline_met"].mean(), 4
                ),
                "latency_mean_ms": round(
                    pd.to_numeric(
                        completed["total_latency_ms"], errors="coerce"
                    ).mean(),
                    2,
                ),
            }
        )
    return pd.DataFrame(rows)


def plot_per_seed(summary: pd.DataFrame, out_dir: Path) -> None:
    pivot = summary.pivot(
        index="seed", columns="variant", values="latency_mean_ms"
    )
    pivot = pivot[
        [c for c in (BASELINE, FULL_ADAPTIVE) if c in pivot]
        + [c for c in pivot if c not in (BASELINE, FULL_ADAPTIVE)]
    ]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    pivot.plot(ax=ax, marker="o", linewidth=1)
    ax.set_title("Mean latency per seed (paired runs)")
    ax.set_xlabel("seed")
    ax.set_ylabel("mean latency (ms)")
    fig.tight_layout()
    out = out_dir / "evaluation_per_seed.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"wrote {out}")


def plot_sensitivity(sens: pd.DataFrame, out_dir: Path) -> None:
    pivot = sens.pivot(
        index="variant", columns="regime", values="deadline_miss_rate"
    )
    fig, ax = plt.subplots(figsize=(9, 4.5))
    pivot.plot.bar(ax=ax)
    ax.set_title("Deadline-miss rate by budget tightness")
    ax.set_ylabel("miss rate")
    ax.set_xlabel("")
    fig.tight_layout()
    out = out_dir / "evaluation_sensitivity.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"wrote {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze evaluation results")
    parser.add_argument("input", type=Path, help="evaluation CSV")
    parser.add_argument(
        "--out-dir", type=Path, default=Path("results/processed")
    )
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    summary = per_run_summary(df)
    summary.to_csv(args.out_dir / "evaluation_per_seed.csv", index=False)

    paired = paired_comparison(summary)
    paired.to_csv(args.out_dir / "paired_comparison.csv", index=False)
    print("Paired comparison (adaptive - baseline):")
    print(paired.to_string(index=False))

    ablation = ablation_table(df)
    ablation.to_csv(args.out_dir / "ablation.csv", index=False)
    print("\nAblation table:")
    print(ablation.to_string(index=False))

    sens = sensitivity_table(df)
    sens.to_csv(args.out_dir / "sensitivity.csv", index=False)
    print("\nSensitivity by budget tightness:")
    print(sens.to_string(index=False))

    plot_per_seed(summary, args.out_dir)
    plot_sensitivity(sens, args.out_dir)


if __name__ == "__main__":
    main()
