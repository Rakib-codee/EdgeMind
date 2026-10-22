# EdgeMind — Project Summary (for CV / applications)

**EdgeMind — Intelligent Edge–Cloud Workload Orchestrator**
Python · FastAPI · Docker · Prometheus/Grafana · pytest · Streamlit
Repo: https://github.com/Rakib-codee/EdgeMind
Live results dashboard: https://edge-cloud-scheduler.streamlit.app

## One-paragraph summary

EdgeMind decides where a computational task should run — local device,
edge server, or cloud — by estimating end-to-end completion latency
(network + queue wait + compute) against each task's deadline, with
explicit admission control for infeasible work. The project treats
evaluation as a first-class engineering problem: policies are compared
under identical workloads with disjoint tuning/held-out/confirmatory
seed sets, seed-level paired bootstrap confidence intervals,
pre-registered experiments, and a real Docker-based worker testbed that
validates whether simulated findings survive contact with measured
wall-clock execution and real queueing.

## CV bullet points (quantified, honest)

- Designed and implemented an adaptive edge–cloud task scheduler
  (Python/FastAPI) with a weighted cost model over estimated latency,
  queue state, and failure risk; reduced simulated deadline misses
  from 27.3% to 2.3% on held-out workloads.
- Built a reproducible evaluation pipeline: 30-seed confirmatory
  simulation with paired bootstrap confidence intervals, disjoint
  tuning/held-out/test seed sets, and per-run provenance manifests
  (git commit, dependency versions, SHA-256 checksums).
- Validated simulation findings against a real testbed of three
  CPU-limited Docker workers (0.25/0.5/1.0 CPU) executing measured
  CPU-bound workloads; a 20-run pre-registered experiment isolated
  queue awareness as the active ingredient (calibration alone degraded
  on-time completion by 6.9 pp).
- Diagnosed and fixed two evaluation bugs (policy-dependent execution
  fairness, queue-wait omission) discovered through statistical
  auditing rather than test failures.
- Reported a null result honestly: on the strict unconditional endpoint
  the adaptive policy is not significantly better than an uncalibrated
  baseline (+1.2 pp, CI crossing zero), because deadline protection is
  paid for by upfront rejection of infeasible tasks.
- Published an interactive results dashboard (Streamlit) presenting
  per-run heterogeneity, confidence intervals, and limitations.

## Skills demonstrated

Distributed-systems scheduling · edge/cloud computing concepts ·
experimental design & applied statistics (paired bootstrap, CIs,
pre-registration) · Docker & container resource limits · REST API
design · monitoring (Prometheus/Grafana) · test-driven development
(60 tests) · reproducible research tooling.

## Short paragraph for a statement of purpose (adapt freely)

"In my EdgeMind project I built an adaptive scheduler for edge–cloud
task offloading and, more importantly, a rigorous evaluation framework
around it. I learned that the hard part of distributed-systems research
is not making a policy look good but proving when and why it helps:
my first real-worker experiment showed that a naive adaptive policy's
apparent advantage disappeared under a fair, pre-registered comparison,
and that queue awareness — not rate calibration — carried the actual
benefit. This experience is why I want to study cloud computing and
distributed systems at the graduate level: I want to do systems work
whose claims survive measurement."
