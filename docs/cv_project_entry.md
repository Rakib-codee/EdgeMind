# CV / LinkedIn Project-Section Entry — EdgeMind

Two formats: LinkedIn Projects field, and a CV/resume bullet version.

---

## 1. LinkedIn "Projects" section

**Project name:**
EdgeMind — Intelligent Edge–Cloud Workload Orchestrator (live demo)

**Description (one line, shows under the name):**
Adaptive task scheduler that routes workloads across local, edge, and
cloud execution targets using real-time latency, load, queue, and
deadline awareness — validated with a statistically rigorous evaluation.

**About / details (paste into the description box):**
Full-stack research system: FastAPI + Next.js 16 dashboard (single
Vercel deployment), Docker-based real-worker testbed (3 CPU-limited
containers), Prometheus/Grafana monitoring, 60-test pytest suite.
Evaluation methodology: tuning/evaluation seed split, ablation
policies, 20-run paired comparisons with run-level bootstrap CIs.
Held-out simulation: deadline misses 27.3% → 2.3%, on-time completion
+11.6pp. Real-worker ablation: queue awareness +8.1pp; calibration
alone −6.9pp (honest null/negative results reported).

**Project URL:**
https://edgemind-eta.vercel.app

**Associated with / skills:** Cloud Computing, Distributed Systems,
System Design, Python, FastAPI, Next.js, TypeScript, Docker, CI/CD,
Experimental Design, Applied Statistics

---

## 2. CV / resume version (4 tight bullets)

**EdgeMind — Intelligent Edge–Cloud Workload Orchestrator**
*Self-directed research project · Live: edgemind-eta.vercel.app*
· Built a full-stack adaptive task scheduler (FastAPI + Next.js 16,
Tailwind, Docker) that routes workloads across local/edge/cloud targets
from real-time latency, load, queue length, and deadlines; deployed as a
single Vercel project (Python serverless + React) with a live 5-page
interactive demo and a 60-test pytest suite.

· Designed a reproducible evaluation pipeline: tuning/evaluation seed
split, ablation policies, pre-registered primary endpoint, run-level
paired bootstrap confidence intervals; on held-out seeds, deadline
misses fell 27.3% → 2.3% (~11.7×) and on-time completion rose +11.6pp.

· Validated on a real Docker worker testbed (3 CPU-limited containers
executing measured CPU-bound work): 20 paired runs across 4 policies
showed queue awareness alone delivers +8.1pp on-time completion, while
rate calibration alone degrades it −6.9pp — reported as an ablation
finding, not hidden.

· Added live observability (Prometheus/Grafana) and a Streamlit results
dashboard; all raw experiment data and historical outputs versioned and
preserved for reproducibility.

---

## 3. One-liner (for CV header or summary line)

Adaptive edge–cloud task scheduler (FastAPI + Next.js + Docker) with a
statistically rigorous 20-run evaluation — deadline misses cut ~11.7×
on held-out data, live at edgemind-eta.vercel.app.
