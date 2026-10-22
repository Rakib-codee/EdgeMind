"""Analysis for the real-worker validation experiment.

Reads results/raw/real_experiment_v1.csv and computes rejection-aware,
measured-latency metrics per (run, policy), plus paired per-run
differences (adaptive - baseline). Runs are the paired unit; with the
small run counts typical of container experiments, differences are
reported per run instead of bootstrapped.

Metric populations (explicit, matching docs/real_worker_experiment.md):
- submitted: all rows for the policy in the run.
- accepted: rows with rejected == False.
- rejected: rows with rejected == True (no latency fields populated).
- successful: accepted rows with success == True.
- on_time: successful rows with deadline_met == True.
- Latency statistics use successful executions only.
"""

import argparse
from pathlib import Path

import pandas as pd


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
        "accepted_deadline_miss_rate": (
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


def paired_differences(summary: pd.DataFrame) -> pd.DataFrame:
    """Per-run adaptive - baseline differences for the primary metrics."""
    metrics = [
        "rejection_rate",
        "overall_success_rate",
        "overall_on_time_rate",
        "accepted_deadline_miss_rate",
        "latency_mean_ms",
        "latency_p95_ms",
        "throughput_tasks_per_s",
        "scheduling_overhead_mean_ms",
    ]
    rows = []
    for run, group in summary.groupby("run"):
        by_policy = group.set_index("policy")
        if not {"baseline", "adaptive"} <= set(by_policy.index):
            continue
        diff = {"run": run}
        for metric in metrics:
            a = by_policy.loc["adaptive", metric]
            b = by_policy.loc["baseline", metric]
            diff[metric] = (
                round(a - b, 4) if pd.notna(a) and pd.notna(b) else None
            )
        rows.append(diff)
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze real-worker experiment")
    parser.add_argument(
        "input", type=Path, default=Path("results/raw/real_experiment_v1.csv"), nargs="?"
    )
    parser.add_argument("--out-dir", type=Path, default=Path("results/processed"))
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    summary = summarize(df)
    diffs = paired_differences(summary)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.out_dir / "real_experiment_v1_summary.csv"
    diffs_path = args.out_dir / "real_experiment_v1_paired_diffs.csv"
    summary.to_csv(summary_path, index=False)
    diffs.to_csv(diffs_path, index=False)

    pd.set_option("display.width", 200)
    print(summary.to_string(index=False))
    print("\npaired differences (adaptive - baseline) per run:")
    print(diffs.to_string(index=False))
    print(f"\nwrote {summary_path} and {diffs_path}")


if __name__ == "__main__":
    main()
