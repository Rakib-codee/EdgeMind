# Real-Worker Validation Experiment

This document describes the containerized real-worker experiment
(`benchmarks/run_real_experiment.py`), which complements the simulation
pipeline with measured wall-clock execution. It does **not** replace or
modify any simulation results. All simulation findings remain
simulation-only; everything in this document is a local Docker
measurement.

## What is measured vs. simulated

| Quantity | Source | Clock |
|---|---|---|
| End-to-end latency (`e2e_latency_ms`) | client wall clock at submit vs. response | `time.time()` |
| Queue wait (`queue_wait_ms`) | worker: enqueue → execution start | `time.perf_counter_ns()` |
| Execution duration (`execution_ms`) | worker: execution start → end | `time.perf_counter_ns()` |
| Scheduling decision cost (`scheduling_overhead_ms`) | client: decision call wall time only | `time.perf_counter_ns()` |

Monotonic clocks are used for durations so NTP adjustments cannot
distort them; wall-clock timestamps (`submit_ts`, `response_ts`, and the
worker's `queued_at`/`started_at`/`finished_at`) are recorded for
ordering and throughput windows. `scheduling_overhead_ms` measures only
the decision function — full scheduling latency (client queuing, HTTP
dispatch) is **not** instrumented and is reported as unavailable.

## Setup

- `compose.real.yaml` starts three workers from the project image with
  CPU limits: `local` 0.25, `edge` 0.5, `cloud` 1.0 CPUs.
- Each worker (`app/real_worker.py`) executes a deterministic SHA-256
  hash chain whose length is proportional to the task's
  `compute_units`, through a single-slot FIFO queue. Workers
  self-calibrate at startup and on demand (`POST /calibrate`); the
  runner recalibrates once per run, outside task measurement, and
  records the per-run rates in the CSV.
- **Network latency is not emulated.** All containers share one Docker
  bridge network; calibrated policies use `network_latency_ms = 0`.
  This is a recorded limitation, not an oversight.

## v2: pre-registered fair comparison

The v2 design separates the effect of **rate calibration** from
**queue-aware scheduling**. Registered before data collection
(commit history predates the v2 run).

### Policies and information access

| | A — original baseline | B — calibrated baseline | C — adaptive | D — ablation (exploratory) |
|---|---|---|---|---|
| Placement rule | min est. latency among feasible | min est. latency among feasible (same `select_target` code path) | min cost = latency + 200·failure_risk (frozen `DEFAULT_WEIGHTS`) | C with failure weight 0 |
| Compute rates | static assumed (10/30/100 units/ms) | per-run measured | per-run measured (same values as B) | per-run measured |
| Queue observation | none | none | own outstanding count | own outstanding count |
| Network latency | static assumed (0/8/35 ms) | 0 | 0 | 0 |
| Feasibility check | est ≤ budget, queue = 0 | est ≤ budget, queue = 0 | est ≤ budget, queue-inclusive | as C |

All policies reject tasks whose estimated latency exceeds the budget;
they differ in estimate accuracy and queue inclusion, not in the
existence of admission control. **B − A isolates calibration;
C − B isolates queue awareness + the failure-risk term; C − A is the
total effect.** D is exploratory, runs last in every run under a fixed
order, and is excluded from primary comparisons. No weights were tuned
on v2 data.

### Protocol

- 20 independent runs × 100 tasks per policy. Workload seed =
  500 + run index (fresh range, disjoint from simulation tuning seeds
  42–51, held-out 100–109, confirmatory 200–229, and Phase 3 seed 42).
- Identical task IDs, compute units, and budgets for all policies
  within a run (verified in analysis).
- `--budget-scale 5`, fixed in Phase 3 before v2 and unchanged.
- A/B/C execution order: Latin square over all six permutations
  (run r → permutation r mod 6); D always last.
- Between policy blocks: all in-flight tasks complete, then a 5 s
  cooldown. Warm-up: worker startup calibration + 2 s idle, unmeasured.
- Recorded per run: measured worker rates, host 1-minute load average
  before/after, Docker version, host OS/arch, CPU limits, container
  image IDs, code commit, dependency versions (manifest).

### Primary outcomes (populations fixed in advance)

1. **Overall on-time completion rate** = on-time successful completions
   / all submitted tasks. *(Primary endpoint.)*
2. **Rejection rate** = rejected / all submitted.
3. **Overall success rate** = successful / all submitted.
4. **Completed-task deadline-miss rate** = 1 − on_time/successful.
   Denominator is *successful completions only* (renamed from the v1
   `accepted_deadline_miss_rate`, which overstated its population).
5. **Mean and p95 end-to-end latency**, successful completions only.
6. **Queue wait** (worker monotonic clock: dequeue → execution start)
   and execution duration, successful completions.
7. **Scheduling decision cost** (decision call only), all tasks.

Both pooled task-level descriptives and per-run summaries are reported.
The **run is the only inferential unit**; individual tasks within a run
are not independent.

### Statistical analysis

Paired run-level percentile bootstrap: resample run indices with
replacement, keeping each sampled run's policy values together;
statistic = mean paired difference; 10,000 replicates; seed 20261022
(recorded). With n = 20 runs, percentile intervals are approximate and
can be narrow-biased; per-run values are reported alongside intervals,
and no significance claim is made from point estimates alone. Three
policy pairs × several metrics are reported; the primary endpoint is
the overall on-time rate for C − B, B − A, C − A.

## v2 results (20 runs, seeds 500–519, budget-scale 5)

Run on the manifest-recorded host (commit and image IDs in
`results/raw/real_experiment_v2.manifest.json`; 8000 raw rows, zero
execution errors). Measured worker rates varied modestly across runs
(local 1.6–3.6, edge 6.5–9.3, cloud 12.4–15.8 units/ms).

Per-policy means of run-level values:

| Metric (population) | A static | B calibrated | C adaptive | D ablation |
|---|---:|---:|---:|---:|
| Rejection rate (submitted) | 0.0% | 0.0% | 59.7% | 60.0% |
| Overall success (submitted) | 100% | 100% | 40.2% | 40.0% |
| **Overall on-time (submitted)** | **20.2%** | **13.3%** | **21.4%** | 20.3% |
| Completed-task miss rate (successful) | 79.8% | 86.7% | 47.0% | 49.1% |
| Mean e2e latency ms (successful) | 1729 | 4099 | 1052 | 1107 |
| p95 e2e latency ms (successful) | 5437 | 7555 | 2487 | 2271 |
| Mean queue wait ms (successful) | 1533 | 3837 | 896 | 922 |
| Decision cost µs (all tasks) | 16 | 21 | 21 | 22 |

Primary paired bootstrap (10,000 replicates, seed 20261022, run-level):

| Comparison | Overall on-time Δ [95% CI] | Rejection Δ | Mean latency Δ ms [95% CI] |
|---|---|---|---|
| B − A (calibration) | −6.9 pp [−8.4, −5.5] | 0 | +2371 [+2206, +2536] |
| C − B (queue awareness) | +8.1 pp [+6.4, +9.6] | +59.8 pp | −3047 [−3246, −2843] |
| C − A (total effect) | +1.2 pp [−0.7, +3.1] | +59.8 pp | −676 [−804, −538] |

Interpretation:

- **Primary endpoint is negative/null:** adaptive (C) does not
  significantly improve overall on-time completion over the original
  baseline (A): +1.2 pp with the interval crossing zero. The v1
  preliminary impression of improvement does not hold under the
  pre-registered design.
- **Calibration alone hurts (B − A).** With accurate rates and no
  queue observation, B sends 100% of tasks to the fastest worker
  (cloud: 2000/2000), its queue explodes (3.8 s mean wait), and
  on-time completion drops 6.9 pp below A. A's *wrong* static rates
  accidentally load-balance (622/699/679 split).
- **Queue awareness is the active ingredient (C − B).** +8.1 pp
  overall on-time and −3.0 s mean latency versus the equally
  calibrated B — but paid for with +59.8 pp rejections.
- **Conditional vs unconditional:** among completed tasks C halves the
  deadline-miss rate (47% vs 80–87%) and cuts mean latency ~40–75%,
  but this population excludes the ~60% of tasks C rejects.
- **Ablation D ≈ C:** removing the failure-risk term changes nothing
  materially — expected, since no execution failures occur in this
  environment.
- Heterogeneity exists per run (e.g. run 13: C 0.17 < A 0.24);
  aggregate claims do not hold uniformly.

## v1: preliminary Phase 3 results (historical, superseded by v2)

The v1 run set (3 runs, policies A and C only, seed 42 workload,
`results/raw/real_experiment_v1.csv`) is preserved unchanged. Its
findings — adaptive rejects 64%, accepted-task miss rate 41.7% vs
80.7%, mean e2e 1131 ms vs 2026 ms — are **preliminary**: 3 runs
cannot characterize variability, and the A-vs-C comparison confounds
calibration with queue awareness (the exact confound v2 separates).
Treat v1 numbers as motivation for v2, not as conclusions.

## Reproducing

```bash
docker compose -f compose.real.yaml up -d --build
python -m benchmarks.run_real_experiment --tasks 100 --runs 20 --seed 500 --budget-scale 5
python -m benchmarks.analyze_real
docker compose -f compose.real.yaml down
```

Outputs: `results/raw/real_experiment_v2.csv` (raw rows),
`results/raw/real_experiment_v2.manifest.json` (provenance: git commit,
host/Docker metadata, dependency versions, config, checksums),
`results/processed/real_experiment_v2_{summary,paired_diffs,bootstrap}.csv`.
Raw results are gitignored. v1 outputs are never overwritten.

## Limitations

- Three containers on one host are **not** a geographically distributed
  edge–cloud deployment. No wide-area latency, no independent machines.
- Results vary with host load, Docker CPU throttling, OS scheduling,
  and machine configuration; absolute numbers are host-specific.
- Identical task inputs do not guarantee identical runtime
  trajectories: host load drifts between policy blocks within a run;
  counterbalancing, not pairing, mitigates this.
- The workload's CPU-bound hash chain stresses CPU only — no memory,
  I/O, or network transfer costs.
- Worker rates are recalibrated per run but constant within a run.
- No execution failures have been observed in any real run; the
  failure-risk term of the adaptive cost is a modeled penalty with no
  measured real-world failures to validate against.
- Resource utilization and full scheduling latency are not
  instrumented (reported as unavailable).
- n = 20 runs supports approximate intervals, not tight inference;
  p95 per run rests on few tail observations when the successful
  population is small.
