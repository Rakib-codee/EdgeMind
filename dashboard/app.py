"""EdgeMind public results dashboard (Streamlit).

Reads committed aggregate tables from dashboard/data/ — never raw
experiment files — and presents the simulation and real-worker
findings with their statistical caveats intact.

Run locally:  streamlit run dashboard/app.py
Deploy: Streamlit Community Cloud, main file dashboard/app.py.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import sys

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# The dashboard deploys from the repo root on Streamlit Cloud; make the
# project package importable so the playground runs the REAL scheduler
# code (not a reimplementation).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.task import TaskRequest
from app.scheduler import (
    DEFAULT_NODES,
    DynamicEnvironment,
    select_target,
    select_target_adaptive,
)
from app.scheduler.environment import NodeState

DATA = Path(__file__).resolve().parent / "data"

st.set_page_config(page_title="EdgeMind — Results", page_icon="🛰️", layout="wide")


@st.cache_data
def load(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / name)


def line_plot(df: pd.DataFrame, ylabel: str) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(6, 3.2))
    df.plot(ax=ax, marker=".", markersize=3, linewidth=1)
    ax.set_ylabel(ylabel)
    ax.set_xlabel("run / seed")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


st.title("EdgeMind — Intelligent Edge–Cloud Workload Orchestrator")
st.caption(
    "Adaptive task scheduling across local / edge / cloud execution targets, "
    "validated by reproducible simulation and a pre-registered Docker "
    "experiment. [Source code](https://github.com/Rakib-codee/EdgeMind)"
)

tab_play, tab_overview, tab_sim, tab_real, tab_method = st.tabs(
    [
        "🎮 Live Playground",
        "Overview",
        "Simulation (30 seeds)",
        "Real Docker workers (20 runs)",
        "Methodology",
    ]
)

# --------------------------------------------------------------- playground
with tab_play:
    st.header("Live Playground — the real scheduler, running now")
    st.caption(
        "This tab imports and executes the actual scheduling code from the "
        "repository (`app/scheduler/`) in your browser session — no mock, no "
        "recording. Task execution timing is simulated with the same model "
        "the benchmark pipeline uses; every decision is computed live."
    )

    st.subheader("1. Submit a task")
    tcol1, tcol2 = st.columns(2)
    with tcol1:
        compute_units = st.slider("Task size (compute units)", 10, 5000, 300, 10)
    with tcol2:
        budget = st.slider("Deadline budget (ms)", 10, 3000, 500, 10)

    st.subheader("2. Current node conditions")
    st.caption("Baseline never sees these — adaptive does.")
    node_cols = st.columns(3)
    states = []
    for col, profile in zip(node_cols, DEFAULT_NODES):
        with col:
            st.markdown(f"**{profile.name}** (rate {profile.compute_rate} u/ms)")
            net = st.slider(
                f"{profile.name} network (ms)", 0, 100,
                int(profile.network_latency_ms), 1, key=f"net_{profile.name}",
            )
            load_f = st.slider(
                f"{profile.name} load factor", 0.3, 2.0, 1.0, 0.1,
                key=f"load_{profile.name}",
            )
            queue = st.slider(
                f"{profile.name} queue length", 0, 10, 0, 1,
                key=f"queue_{profile.name}",
            )
            states.append(
                NodeState(
                    profile=profile,
                    network_latency_ms=float(net),
                    load_factor=load_f,
                    queue_length=queue,
                )
            )

    task = TaskRequest(
        task_id="playground", compute_units=float(compute_units),
        max_latency_ms=float(budget),
    )
    decision_b = select_target(task, DEFAULT_NODES)
    decision_a = select_target_adaptive(task, states)

    st.subheader("3. Decisions (computed live)")
    dcol1, dcol2 = st.columns(2)
    for col, name, dec in [
        (dcol1, "Baseline (static profiles)", decision_b),
        (dcol2, "Adaptive (measured state + queue)", decision_a),
    ]:
        with col:
            st.markdown(f"**{name}**")
            if dec is None:
                st.error("REJECTED — no node estimated feasible within deadline")
            else:
                st.success(
                    f"→ **{dec.selected_target}** "
                    f"(estimated {dec.estimated_latency_ms} ms)"
                )

    from app.scheduler.latency import estimate_latency_ms

    est_rows = []
    for s in states:
        est = estimate_latency_ms(task, s)
        est_rows.append(
            {
                "node": s.name,
                "est. latency (ms)": round(est, 1),
                "feasible": "yes" if est <= budget else "NO",
                "queue": s.queue_length,
                "load": s.load_factor,
            }
        )
    st.dataframe(pd.DataFrame(est_rows), width="stretch", hide_index=True)

    st.divider()
    st.subheader("4. Live mini-benchmark")
    st.caption(
        "Runs 100 generated tasks through BOTH policies on a simulated "
        "dynamic environment, right now, with your seed. Deterministic: "
        "same seed → same result."
    )
    bcol1, bcol2 = st.columns(2)
    with bcol1:
        bench_seed = st.slider("Benchmark seed", 0, 9999, 42)
    with bcol2:
        bench_tasks = st.slider("Tasks", 50, 300, 100, 50)

    if st.button("▶ Run live benchmark"):
        import random as _random

        from benchmarks.run_benchmark import generate_tasks, run_policy

        tasks = generate_tasks(bench_tasks, bench_seed)
        result_rows = {}
        for policy in ("baseline", "adaptive"):
            rows = run_policy(policy, tasks, bench_seed)
            df = pd.DataFrame(rows)
            rejected = df["rejected"].astype(bool)
            accepted = df[~rejected]
            successful = accepted[accepted["success"].astype(bool)]
            on_time = successful[successful["deadline_met"].astype(bool)]
            lat = pd.to_numeric(successful["total_latency_ms"], errors="coerce")
            result_rows[policy] = {
                "rejected": f"{rejected.mean():.0%}",
                "overall on-time": f"{len(on_time) / len(df):.0%}",
                "miss rate (completed)": f"{1 - len(on_time) / max(len(successful), 1):.0%}",
                "mean latency (ms)": f"{lat.mean():.1f}",
                "p95 latency (ms)": f"{lat.quantile(0.95):.1f}",
            }
        st.dataframe(
            pd.DataFrame(result_rows).rename_axis("metric"),
            width="stretch",
        )

# ---------------------------------------------------------------- overview
with tab_overview:
    st.markdown(
        """
**Research question:** when network latency and server load vary, can an
adaptive scheduling policy improve deadline compliance over static
rule-based placement?

**What EdgeMind does:** for each incoming task it estimates end-to-end
completion latency on every candidate node (network + queue wait +
compute), rejects tasks whose deadlines are infeasible, and places the
rest on the lowest-cost node using measured node state.

**Headline evidence:**
- *Simulation, 30 held-out seeds, paired design:* adaptive cuts the
  accepted-task deadline-miss rate by ~27 pp and raises overall
  on-time completion by ~12 pp, with bootstrap CIs excluding zero.
- *Real Docker workers, 20 pre-registered runs:* the benefit comes
  from **queue awareness**, not calibration alone — and on the strict
  unconditional endpoint (on-time over all submitted tasks) adaptive
  is *not* significantly better than the uncalibrated baseline,
  because it honestly rejects ~60% of tasks with infeasible deadlines.
"""
    )
    st.info(
        "All numbers in this dashboard come from committed aggregate "
        "tables exported by the analysis pipeline (`benchmarks/export_dashboard_data.py`)."
    )

# --------------------------------------------------------------- simulation
with tab_sim:
    st.header("Simulation — 30-seed confirmatory evaluation")
    st.caption(
        "Seeds 200–229, disjoint from tuning (42–51) and held-out "
        "(100–109) sets. 300 tasks per policy-variant per seed. "
        "Simulated latencies — not physical measurements."
    )

    paired = load("sim_paired_comparison.csv")
    st.subheader("Paired differences (adaptive − baseline), seed-level bootstrap")
    show = paired.copy()
    for c in ("mean_diff", "ci95_low", "ci95_high"):
        show[c] = show[c].round(4)
    st.dataframe(show, width="stretch", hide_index=True)

    per_seed = load("sim_per_seed.csv")
    base = per_seed[per_seed.variant == "baseline"].set_index("seed")
    adap = per_seed[per_seed.variant == "adaptive"].set_index("seed")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Overall on-time rate per seed")
        chart = pd.DataFrame(
            {"baseline": base.overall_ontime_rate, "adaptive": adap.overall_ontime_rate}
        )
        st.pyplot(line_plot(chart, "on-time rate"))
    with col2:
        st.subheader("Mean latency per seed (ms, accepted tasks)")
        chart = pd.DataFrame(
            {"baseline": base.latency_mean_ms, "adaptive": adap.latency_mean_ms}
        )
        st.pyplot(line_plot(chart, "ms"))

    st.subheader("Scenario-level paired differences")
    st.dataframe(load("sim_scenario_paired.csv"), width="stretch", hide_index=True)

# ------------------------------------------------------------- real workers
with tab_real:
    st.header("Real Docker workers — pre-registered 20-run experiment")
    st.caption(
        "Three CPU-limited containers (0.25 / 0.5 / 1.0 CPU) executing "
        "real SHA-256 work. Measured wall-clock latency and queueing. "
        "Local Docker — NOT a distributed edge-cloud deployment."
    )

    st.subheader("Policies")
    st.markdown(
        """
| Policy | Rates | Queue view | Admission |
|---|---|---|---|
| **A** original baseline | static assumed (10/30/100 u/ms) | none | feasibility on static estimates |
| **B** calibrated baseline | measured per run | none | feasibility on measured rates |
| **C** adaptive | measured per run | own outstanding queue | queue-inclusive feasibility + risk cost |
| **D** ablation (exploratory) | as C | as C | as C, failure weight = 0 |
"""
    )

    summary = load("real_v2_summary.csv")
    cols = [
        "rejection_rate", "overall_success_rate", "overall_on_time_rate",
        "completed_deadline_miss_rate", "latency_mean_ms", "latency_p95_ms",
        "queue_wait_mean_ms",
    ]
    st.subheader("Per-policy means over 20 runs")
    st.dataframe(
        summary.groupby("policy")[cols].mean().round(3),
        width="stretch",
    )

    st.subheader("Per-run overall on-time rate")
    piv = summary.pivot(index="run", columns="policy", values="overall_on_time_rate")
    st.pyplot(line_plot(piv[["A", "B", "C"]], "on-time rate"))

    st.subheader("Paired bootstrap 95% CIs (run-level, 10,000 replicates)")
    boot = load("real_v2_bootstrap.csv")
    st.dataframe(boot.round(4), width="stretch", hide_index=True)

    st.warning(
        "Primary endpoint (C − A, overall on-time): +1.2 pp "
        "[−0.7, +3.1] — NOT statistically distinguishable from zero. "
        "Adaptive's deadline protection is real among completed tasks "
        "but is paid for by rejecting ~60% of submissions."
    )

# -------------------------------------------------------------- methodology
with tab_method:
    st.header("Methodology & limitations")
    st.markdown(
        """
**Statistical practice**
- Tuning seeds (42–51), held-out seeds (100–109), and confirmatory
  seeds (200–229) are disjoint; weights were frozen before final runs.
- The run/seed is the independent unit — never individual tasks.
- Paired percentile bootstrap (seed- or run-level resampling);
  replicates and seeds recorded (real experiment: 10,000 replicates,
  seed 20261022).
- Every metric reports its population: rejected, accepted, successful,
  and on-time tasks are counted separately; latency statistics cover
  successful completions only.

**Reproducibility**
- Every run writes a manifest: git commit, Python/dependency versions,
  host and Docker metadata, config, SHA-256 checksums of outputs.
- Raw CSVs are local (gitignored); the aggregates shown here are
  exported by `benchmarks/export_dashboard_data.py`.

**Limitations**
- Simulation results are simulated — no claim about physical networks.
- Real-worker results come from three containers on one host; absolute
  numbers are host-specific; network latency is not emulated.
- 20 runs give approximate percentile intervals, not tight inference.
- Resource utilization and full scheduling latency are not instrumented.
- No execution failures were observed in real runs, so the failure-risk
  term remains simulation-validated only.
"""
    )
    st.markdown(
        "Full details: `docs/evaluation.md`, `docs/methodology.md`, "
        "`docs/real_worker_experiment.md` in the repository."
    )
