"""Tests for real-experiment metric calculations and record handling."""

import pandas as pd
import pytest

from app.real_worker import iterations_for
from benchmarks.analyze_real import (
    _bool_series,
    paired_differences,
    run_metrics,
    summarize,
)


def _row(run=0, policy="baseline", **overrides):
    row = {
        "run": run,
        "policy": policy,
        "task_id": "t0",
        "rejected": False,
        "success": True,
        "deadline_met": True,
        "e2e_latency_ms": 10.0,
        "queue_wait_ms": 1.0,
        "execution_ms": 8.0,
        "scheduling_overhead_ms": 0.1,
        "submit_ts": 1.0,
        "response_ts": 1.01,
    }
    row.update(overrides)
    return row


def test_iterations_for_scales_with_units():
    assert iterations_for(1.0) == 200
    assert iterations_for(2.5) == 500
    # Tiny tasks still get at least one iteration (no zero-work records).
    assert iterations_for(0.0001) == 1


def test_bool_series_parses_strings_and_bools():
    s = pd.Series(["True", "False", True, False])
    assert _bool_series(s).tolist() == [True, False, True, False]


def test_run_metrics_populations():
    group = pd.DataFrame(
        [
            _row(task_id="t0"),  # success, on time
            _row(task_id="t1", deadline_met=False, e2e_latency_ms=30.0),  # late
            _row(task_id="t2", success=False, deadline_met=False,
                 e2e_latency_ms="", queue_wait_ms="", execution_ms=""),
            _row(task_id="t3", rejected=True, success=False, deadline_met=False,
                 e2e_latency_ms="", queue_wait_ms="", execution_ms="",
                 submit_ts="", response_ts=""),
        ]
    )
    m = run_metrics(group)
    assert m["submitted"] == 4
    assert m["accepted"] == 3
    assert m["rejected"] == 1
    assert m["rejection_rate"] == 0.25
    assert m["successful"] == 2
    assert m["failed"] == 1
    assert m["on_time"] == 1
    assert m["accepted_deadline_miss_rate"] == 0.5
    assert m["overall_success_rate"] == 0.5
    assert m["overall_on_time_rate"] == 0.25
    # Latency population = successful executions only.
    assert m["latency_mean_ms"] == 20.0


def test_run_metrics_all_rejected_is_safe():
    group = pd.DataFrame(
        [
            _row(task_id=f"t{i}", rejected=True, success=False, deadline_met=False,
                 e2e_latency_ms="", queue_wait_ms="", execution_ms="",
                 submit_ts="", response_ts="")
            for i in range(3)
        ]
    )
    m = run_metrics(group)
    assert m["rejection_rate"] == 1.0
    assert m["overall_success_rate"] == 0.0
    assert m["latency_mean_ms"] is None
    assert m["accepted_deadline_miss_rate"] is None


def test_malformed_latency_cells_are_excluded_not_zero():
    group = pd.DataFrame(
        [
            _row(task_id="t0", e2e_latency_ms=10.0),
            _row(task_id="t1", e2e_latency_ms="not-a-number"),
        ]
    )
    m = run_metrics(group)
    # One valid latency observation; the malformed cell must not count as 0.
    assert m["latency_mean_ms"] == 10.0


def test_paired_differences_require_both_policies():
    df = pd.DataFrame(
        [
            _row(run=0, policy="baseline"),
            _row(run=0, policy="adaptive", e2e_latency_ms=20.0),
            _row(run=1, policy="baseline"),  # no adaptive partner
        ]
    )
    diffs = paired_differences(summarize(df))
    assert diffs["run"].tolist() == [0]
    assert diffs.iloc[0]["latency_mean_ms"] == pytest.approx(10.0)
