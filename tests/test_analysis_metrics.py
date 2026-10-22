"""Tests for rejection-aware metric calculation in analysis scripts."""

import pandas as pd

from benchmarks.analyze_evaluation import per_run_summary


def _row(task_id, rejected=False, success=True, deadline_met=True, latency=10.0):
    return {
        "seed": 1,
        "variant": "v",
        "task_id": task_id,
        "rejected": rejected,
        "success": success,
        "deadline_met": deadline_met,
        "total_latency_ms": "" if rejected else latency,
    }


def test_rejection_aware_metrics_use_all_submitted_tasks():
    # 4 submitted: 1 rejected, 1 success+ontime, 1 success+miss, 1 failed.
    df = pd.DataFrame(
        [
            _row("t0", rejected=True),
            _row("t1", success=True, deadline_met=True),
            _row("t2", success=True, deadline_met=False),
            _row("t3", success=False, deadline_met=False),
        ]
    )
    row = per_run_summary(df).iloc[0]

    assert row["tasks"] == 4
    assert row["scheduled"] == 3
    assert row["rejection_rate"] == 0.25
    # accepted-task metrics use only the 3 executed tasks
    assert row["accepted_deadline_miss_rate"] == round(2 / 3, 4)
    assert row["accepted_success_rate"] == round(2 / 3, 4)
    # overall metrics use all 4 submitted tasks
    assert row["overall_ontime_rate"] == 0.25
    assert row["overall_success_rate"] == 0.5
    assert row["overall_deadline_failure_rate"] == 0.75
    # latency population: executed tasks only
    assert row["latency_mean_ms"] == 10.0


def test_metrics_do_not_count_tasks_twice():
    df = pd.DataFrame([_row(f"t{i}") for i in range(10)])
    row = per_run_summary(df).iloc[0]
    assert row["tasks"] == 10
    assert row["overall_ontime_rate"] == 1.0
    assert row["overall_deadline_failure_rate"] == 0.0
