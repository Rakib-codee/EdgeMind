"""Tests for the dashboard data export."""

from pathlib import Path

import pandas as pd
import pytest

from benchmarks.export_dashboard_data import EXPORTS, export

DATA = Path(__file__).resolve().parent.parent / "dashboard" / "data"


@pytest.fixture(scope="module", autouse=True)
def _exported():
    export()


def test_all_exports_exist_and_are_small():
    for _, name in EXPORTS:
        path = DATA / name
        assert path.exists(), name
        assert path.stat().st_size < 100_000, f"{name} too large to commit"


def test_sim_paired_comparison_has_cis():
    df = pd.read_csv(DATA / "sim_paired_comparison.csv")
    assert {"metric", "mean_diff", "ci95_low", "ci95_high", "n_seeds"} <= set(df.columns)
    assert (df["n_seeds"] == 30).all()
    assert not df[["mean_diff", "ci95_low", "ci95_high"]].isna().any().any()
    # Headline confirmatory result: adaptive misses fewer deadlines.
    miss = df[df.metric == "accepted_deadline_miss_rate"].iloc[0]
    assert miss["mean_diff"] < 0 and miss["ci95_high"] < 0


def test_real_bootstrap_table_structure():
    df = pd.read_csv(DATA / "real_v2_bootstrap.csv")
    assert {"comparison", "metric", "n_runs", "mean_diff", "ci_low", "ci_high"} <= set(
        df.columns
    )
    assert (df["n_runs"] == 20).all()
    assert set(df["comparison"].unique()) == {"B-A", "C-B", "C-A"}


def test_real_summary_covers_four_policies():
    df = pd.read_csv(DATA / "real_v2_summary.csv")
    assert set(df["policy"].unique()) == {"A", "B", "C", "D"}
    assert df["run"].nunique() == 20
    assert not df["overall_on_time_rate"].isna().any()


def test_per_seed_table_is_seed_grained():
    df = pd.read_csv(DATA / "sim_per_seed.csv")
    assert {"seed", "variant", "overall_ontime_rate"} <= set(df.columns)
    assert df["seed"].nunique() == 30
