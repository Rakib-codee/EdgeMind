# Methodology — EdgeMind

## Research question

> When network latency and server load vary, can adaptive task
> scheduling reduce task completion latency compared to a static
> rule-based policy?

This is a hypothesis to test, not a pre-decided conclusion. The
evaluation (see `docs/evaluation.md`) found the adaptive policy reduces
the **deadline-miss rate** significantly while **increasing mean
latency** — a genuine trade-off, reported as measured.

## System model

- A client generates tasks described by `compute_units` (work) and
  `max_latency_ms` (deadline).
- Three execution targets exist: local, edge, cloud. Each has a static
  profile (network latency, compute rate) and a dynamic state (current
  latency, load factor, queue length).
- The environment evolves per simulated tick via mean-reverting random
  walks (latency spikes, load drift), giving reproducible congestion
  scenarios without real infrastructure.

## Scheduling objective and constraints

**Objective:** choose a node that completes the task within its latency
budget while preferring low latency and low risk.

**Hard constraint:** estimated latency ≤ `max_latency_ms` (feasibility).
Tasks with no feasible node are rejected (HTTP 422).

**Baseline policy:** among feasible nodes, pick the lowest estimated
latency using static node profiles only. It never reacts to current
load or queue.

**Adaptive policy:** among feasible nodes, pick the lowest cost

```
cost = estimated_latency
     + w_load    * max(0, load_factor - 1)
     + w_failure * failure_probability
```

with default weights `w_load = 0 ms`, `w_failure = 200 ms`
(latency-equivalent units, interpretable by design; tuned by grid
search on dedicated tuning seeds with an admission-aware objective —
see `docs/evaluation.md`). The load penalty defaults to 0 because load
is already priced into the estimate via `compute_rate / load_factor`.
Estimated latency includes queue wait:
`network + service * (1 + queue_length)`; simulated execution applies
the same model, so estimates and execution are consistent.

## Assumptions

- Node capacities and latencies are stylised simulation parameters, not
  measured values.
- Queue wait assumes queued tasks are of similar size.
- Failure probability combines a base drop rate with overload and queue
  pressure: `0.01 + 0.05 * max(0, load - 1) + 0.02 * queue_length`,
  capped at 0.5.
- Execution adds 10% overhead plus ±5% jitter (seedable RNG).

## Related approaches (context)

Edge–cloud task offloading is widely studied: latency-minimizing
heuristics (e.g. MELODY-style latency-aware offloading), load-aware
dispatch, and learning-based policies (Q-learning, DRL) are common.
EdgeMind deliberately starts with an **interpretable weighted heuristic**
rather than ML: it is explainable, cheap, and provides a defensible
baseline before considering learning-based policies. Learning-based
scheduling remains future work.

## Threats to validity

- **Construct validity:** simulated latency is not physical network
  latency; conclusions apply to the simulated model.
- **Internal validity:** identical seeds and workloads per policy give
  paired comparison; residual risk that environment dynamics favour one
  policy class.
- **External validity:** three stylised nodes and synthetic workloads
  do not generalise to production infrastructure.
- **Conclusion validity:** 10 seeds provide modest power; bootstrap CIs
  are reported alongside point estimates.
