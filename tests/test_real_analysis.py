"""Tests for real-experiment metric calculations and record handling."""

import pandas as pd
import pytest

from app.models.task import TaskRequest
from app.real_worker import iterations_for
from app.scheduler import DEFAULT_NODES, select_target
from app.scheduler.nodes import NodeProfile
from benchmarks.analyze_real import (
    _bool_series,
    bootstrap_paired_ci,
    paired_differences,
    run_metrics,
    summarize,
)
from benchmarks.run_real_experiment import (
    PERMUTATIONS,
    POLICY_LABELS,
    decide,
    policy_order,
)


def _row(run=0, policy="A", **overrides):
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
    assert m["completed_deadline_miss_rate"] == 0.5
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
    assert m["completed_deadline_miss_rate"] is None


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
            _row(run=0, policy="B"),
            _row(run=0, policy="A", e2e_latency_ms=20.0),
            _row(run=1, policy="B"),  # no A partner
        ]
    )
    diffs = paired_differences(summarize(df), pairs=[("B", "A")])
    assert diffs["run"].tolist() == [0]
    assert diffs.iloc[0]["comparison"] == "B-A"
    assert diffs.iloc[0]["latency_mean_ms"] == pytest.approx(-10.0)


# --- Policy definitions and order -------------------------------------

def test_policy_b_uses_baseline_code_path_with_measured_rates():
    """B must be the baseline algorithm; only the profiles differ."""
    task = TaskRequest(task_id="t", compute_units=50.0, max_latency_ms=1000.0)
    rates = {"local": 2.0, "edge": 7.0, "cloud": 14.0}
    decision = decide("B", task, rates, {"local": 0, "edge": 0, "cloud": 0})
    expected = select_target(
        task,
        tuple(
            NodeProfile(name=n, network_latency_ms=0.0, compute_rate=r)
            for n, r in rates.items()
        ),
    )
    assert decision == expected
    assert decision.scheduler == "baseline"
    assert decision.selected_target == "cloud"


def test_policy_a_uses_static_default_nodes():
    task = TaskRequest(task_id="t", compute_units=50.0, max_latency_ms=1000.0)
    decision = decide("A", task, {"local": 2.0}, {"local": 0})
    assert decision == select_target(task, DEFAULT_NODES)


def test_policy_order_covers_all_permutations_and_d_last():
    seen = {policy_order(r)[:3] for r in range(6)}
    assert seen == set(PERMUTATIONS)
    for r in range(20):
        order = policy_order(r)
        assert order[-1] == "D"
        assert sorted(order[:3]) == ["A", "B", "C"]
    assert set(POLICY_LABELS) == {"A", "B", "C", "D"}


# --- Bootstrap ----------------------------------------------------------

def _summary_for_bootstrap(n_runs=20, effect=0.1):
    rows = []
    for r in range(n_runs):
        rows.append({"run": r, "policy": "A", "overall_on_time_rate": 0.2})
        rows.append(
            {"run": r, "policy": "B", "overall_on_time_rate": 0.2 + effect}
        )
    return pd.DataFrame(rows)


def test_bootstrap_is_reproducible_with_fixed_seed():
    summary = _summary_for_bootstrap()
    a = bootstrap_paired_ci(summary, ("B", "A"), "overall_on_time_rate")
    b = bootstrap_paired_ci(summary, ("B", "A"), "overall_on_time_rate")
    assert a == b
    assert a["n_runs"] == 20
    assert a["mean_diff"] == pytest.approx(0.1)
    # Constant positive effect: interval excludes zero.
    assert a["ci_low"] > 0


def test_bootstrap_keeps_run_pairs_together():
    """Resampling must never pair run i of one policy with run j of another."""
    rows = []
    for r in range(20):
        rows.append({"run": r, "policy": "A", "overall_on_time_rate": r / 100})
        rows.append({"run": r, "policy": "B", "overall_on_time_rate": 1.0 - r / 100})
    summary = pd.DataFrame(rows)
    result = bootstrap_paired_ci(summary, ("B", "A"), "overall_on_time_rate")
    # Paired per-run diffs are all 1 - 2r/100; mean over uniform runs is 0.81.
    assert result["mean_diff"] == pytest.approx(0.81, abs=1e-3)


def test_bootstrap_handles_missing_pair():
    summary = _summary_for_bootstrap()
    result = bootstrap_paired_ci(summary, ("C", "A"), "overall_on_time_rate")
    assert result["n_runs"] == 0
    assert result["mean_diff"] is None
