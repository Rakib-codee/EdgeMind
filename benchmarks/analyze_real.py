"""Analysis for the real-worker validation experiment (v2).

Reads results/raw/real_experiment_v2.csv and computes rejection-aware,
measured-latency metrics per (run, policy), paired per-run differences
for the pre-registered policy comparisons, and run-level paired
bootstrap confidence intervals.

Pre-registered comparisons (primary policies only):
- B - A: effect of worker-rate calibration.
- C - B: effect of queue awareness + failure-risk cost term.
- C - A: total effect of the adaptive policy.
Policy D is exploratory and excluded from primary intervals.

Metric populations (explicit):
- submitted: all rows for the policy in the run.
- accepted: rows with rejected == False.
- rejected: rows with rejected == True (latency fields structurally
  absent, not zero).
- successful: accepted rows with success == True.
- on_time: successful rows with deadline_met == True.
- completed_deadline_miss_rate: 1 - on_time/successful; denominator is
  successful completions only (renamed from the Phase 3
  accepted_deadline_miss_rate to state its actual population).
- Latency statistics use successful executions only.

Inference: the run is the independent experimental unit. Bootstrap
resamples run indices with replacement, keeping all policy results of
a sampled run together (paired design). Percentile intervals with
n=20 runs are approximate; per-run values are reported alongside.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

PRIMARY_PAIRS = [("B", "A"), ("C", "B"), ("C", "A")]
BOOTSTRAP_SEED = 20261022
BOOTSTRAP_REPLICATES = 10_000

BOOTSTRAP_METRICS = [
    "overall_on_time_rate",
    "rejection_rate",
    "overall_success_rate",
    "completed_deadline_miss_rate",
    "latency_mean_ms",
    "latency_p95_ms",
    "queue_wait_mean_ms",
    "scheduling_overhead_mean_ms",
]


def _bool_series(s: pd.Series) -> pd.Series:
    """Parse CSV boolean cells robustly (True/False strings or bools)."""
    if s.dtype == bool:
        return s
    return s.astype(str).str.lower().map({"true": True, "false": False})


def run_metrics(group: pd.DataFrame) -> dict:
    """Metrics for one (run, policy) slice of the experiment CSV."""
    submitted = len(group)
    rejected = _bool_series(group["rejected"])
    accepted = group[~rejected]
    n_accepted = len(accepted)
    n_rejected = submitted - n_accepted

    success = _bool_series(accepted["success"])
    successful = accepted[success]
    deadline_met = _bool_series(successful["deadline_met"])
    on_time = successful[deadline_met]

    latency = pd.to_numeric(successful["e2e_latency_ms"], errors="coerce").dropna()
    queue_wait = pd.to_numeric(successful["queue_wait_ms"], errors="coerce").dropna()
    execution = pd.to_numeric(successful["execution_ms"], errors="coerce").dropna()
    overhead = pd.to_numeric(group["scheduling_overhead_ms"], errors="coerce").dropna()

    submit = pd.to_numeric(accepted["submit_ts"], errors="coerce")
    response = pd.to_numeric(accepted["response_ts"], errors="coerce")
    window_s = (response.max() - submit.min()) if n_accepted else float("nan")
    throughput = n_accepted / window_s if window_s and window_s > 0 else float("nan")

    return {
        "submitted": submitted,
        "accepted": n_accepted,
        "rejected": n_rejected,
        "rejection_rate": round(n_rejected / submitted, 4) if submitted else None,
        "successful": len(successful),
        "failed": n_accepted - len(successful),
        "on_time": len(on_time),
        "completed_deadline_miss_rate": (
            round(1 - deadline_met.mean(), 4) if len(successful) else None
        ),
        "overall_success_rate": (
            round(len(successful) / submitted, 4) if submitted else None
        ),
        "overall_on_time_rate": (
            round(len(on_time) / submitted, 4) if submitted else None
        ),
        "latency_mean_ms": round(latency.mean(), 2) if len(latency) else None,
        "latency_median_ms": round(latency.median(), 2) if len(latency) else None,
        "latency_p95_ms": round(latency.quantile(0.95), 2) if len(latency) else None,
        "queue_wait_mean_ms": round(queue_wait.mean(), 2) if len(queue_wait) else None,
        "execution_mean_ms": round(execution.mean(), 2) if len(execution) else None,
        "scheduling_overhead_mean_ms": round(overhead.mean(), 3) if len(overhead) else None,
        "throughput_tasks_per_s": round(throughput, 3),
    }


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (run, policy), group in df.groupby(["run", "policy"]):
        rows.append({"run": run, "policy": policy, **run_metrics(group)})
    return pd.DataFrame(rows)


def paired_differences(
    summary: pd.DataFrame,
    pairs: list[tuple[str, str]] | None = None,
    metrics: list[str] | None = None,
) -> pd.DataFrame:
    """Per-run differences (policy_x - policy_y) for each pair."""
    pairs = pairs or PRIMARY_PAIRS
    metrics = metrics or BOOTSTRAP_METRICS + ["throughput_tasks_per_s"]
    rows = []
    for run, group in summary.groupby("run"):
        by_policy = group.set_index("policy")
        for x, y in pairs:
            if not {x, y} <= set(by_policy.index):
                continue
            diff = {"run": run, "comparison": f"{x}-{y}"}
            for metric in metrics:
                a = by_policy.loc[x, metric]
                b = by_policy.loc[y, metric]
                diff[metric] = (
                    round(a - b, 4) if pd.notna(a) and pd.notna(b) else None
                )
            rows.append(diff)
    return pd.DataFrame(rows)


def bootstrap_paired_ci(
    summary: pd.DataFrame,
    pair: tuple[str, str],
    metric: str,
    n_boot: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> dict:
    """Paired percentile bootstrap CI for a run-level mean difference.

    Resamples run indices with replacement, keeping each sampled run's
    two policy values together; the statistic is the mean paired
    difference. Deterministic for a fixed seed.
    """
    x, y = pair
    wide = summary.pivot(index="run", columns="policy", values=metric)
    if not {x, y} <= set(wide.columns):
        return {"comparison": f"{x}-{y}", "metric": metric, "n_runs": 0,
                "mean_diff": None, "ci_low": None, "ci_high": None}
    wide = wide.dropna(subset=[x, y])
    diffs = (wide[x] - wide[y]).to_numpy()
    n = len(diffs)
    if n == 0:
        return {"comparison": f"{x}-{y}", "metric": metric, "n_runs": 0,
                "mean_diff": None, "ci_low": None, "ci_high": None}
    rng = np.random.default_rng(seed)
    boot = rng.choice(diffs, size=(n_boot, n), replace=True).mean(axis=1)
    return {
        "comparison": f"{x}-{y}",
        "metric": metric,
        "n_runs": n,
        "mean_diff": round(float(diffs.mean()), 4),
        "ci_low": round(float(np.percentile(boot, 2.5)), 4),
        "ci_high": round(float(np.percentile(boot, 97.5)), 4),
    }


def bootstrap_table(
    summary: pd.DataFrame,
    pairs: list[tuple[str, str]] | None = None,
    metrics: list[str] | None = None,
    n_boot: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> pd.DataFrame:
    pairs = pairs or PRIMARY_PAIRS
    metrics = metrics or BOOTSTRAP_METRICS
    return pd.DataFrame(
        [
            bootstrap_paired_ci(summary, pair, metric, n_boot, seed)
            for pair in pairs
            for metric in metrics
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze real-worker experiment v2")
    parser.add_argument(
        "input", type=Path, default=Path("results/raw/real_experiment_v2.csv"), nargs="?"
    )
    parser.add_argument("--out-dir", type=Path, default=Path("results/processed"))
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    summary = summarize(df)
    diffs = paired_differences(summary)
    boot = bootstrap_table(summary)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, table in [
        ("summary", summary),
        ("paired_diffs", diffs),
        ("bootstrap", boot),
    ]:
        path = args.out_dir / f"real_experiment_v2_{name}.csv"
        table.to_csv(path, index=False)
        paths[name] = path

    pd.set_option("display.width", 250)
    print(summary.to_string(index=False))
    print("\npaired differences per run:")
    print(diffs.to_string(index=False))
    print("\nbootstrap 95% CIs (run-level paired percentile, "
          f"{BOOTSTRAP_REPLICATES} replicates, seed {BOOTSTRAP_SEED}):")
    print(boot.to_string(index=False))
    for name, path in paths.items():
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
