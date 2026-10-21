"""Analyze benchmark results.

Computes mean/median/p95 latency, deadline-miss rate, success rate,
and target distribution per policy, and renders comparison plots.
"""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for policy, group in df.groupby("policy"):
        completed = group[group["rejected"] == False]  # noqa: E712
        latency = pd.to_numeric(completed["total_latency_ms"], errors="coerce")
        rows.append(
            {
                "policy": policy,
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
                "throughput_tasks_per_s": round(
                    len(completed) / (latency.sum() / 1000), 3
                ),
            }
        )
    return pd.DataFrame(rows)


def plot_latency(df: pd.DataFrame, out_dir: Path) -> None:
    completed = df[df["rejected"] == False]  # noqa: E712
    latency = pd.to_numeric(completed["total_latency_ms"], errors="coerce")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    policies = sorted(completed["policy"].unique())

    axes[0].boxplot(
        [latency[completed["policy"] == p] for p in policies],
        tick_labels=policies,
    )
    axes[0].set_title("Task latency by policy")
    axes[0].set_ylabel("latency (ms)")

    miss_rates = [
        1 - completed[completed["policy"] == p]["deadline_met"].mean()
        for p in policies
    ]
    axes[1].bar(policies, miss_rates)
    axes[1].set_title("Deadline-miss rate by policy")
    axes[1].set_ylabel("miss rate")

    fig.tight_layout()
    out = out_dir / "latency_comparison.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"wrote {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze benchmark results")
    parser.add_argument("input", type=Path, help="raw benchmark CSV")
    parser.add_argument("--out-dir", type=Path, default=Path("results/processed"))
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    summary = summarize(df)
    summary_path = args.out_dir / "summary.csv"
    summary.to_csv(summary_path, index=False)
    print(summary.to_string(index=False))
    print(f"wrote {summary_path}")

    plot_latency(df, args.out_dir)


if __name__ == "__main__":
    main()
