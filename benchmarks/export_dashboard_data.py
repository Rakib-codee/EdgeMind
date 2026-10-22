"""Export aggregate result tables for the public dashboard.

Raw experiment CSVs are gitignored (large, local). The Streamlit
dashboard needs only small aggregate tables, which this script copies
from results/processed/ into dashboard/data/ with stable, prefixed
names. Run after regenerating any analysis outputs.

Nothing here recomputes metrics — it only copies already-validated
analysis outputs, so the dashboard can never diverge silently from
the analysis pipeline.
"""

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "results" / "processed"
DST = ROOT / "dashboard" / "data"

# (source relative to results/processed, exported name)
EXPORTS = [
    # Simulation: 30-seed confirmatory evaluation (primary sim evidence).
    ("confirmatory_v1/ablation.csv", "sim_ablation.csv"),
    ("confirmatory_v1/evaluation_per_seed.csv", "sim_per_seed.csv"),
    ("confirmatory_v1/paired_comparison.csv", "sim_paired_comparison.csv"),
    ("confirmatory_v1/scenario_paired.csv", "sim_scenario_paired.csv"),
    ("confirmatory_v1/sensitivity.csv", "sim_sensitivity.csv"),
    # Real-worker v2: pre-registered 20-run Docker experiment.
    ("real_experiment_v2_summary.csv", "real_v2_summary.csv"),
    ("real_experiment_v2_paired_diffs.csv", "real_v2_paired_diffs.csv"),
    ("real_experiment_v2_bootstrap.csv", "real_v2_bootstrap.csv"),
]


def export() -> list[Path]:
    DST.mkdir(parents=True, exist_ok=True)
    written = []
    for src_rel, dst_name in EXPORTS:
        src = SRC / src_rel
        if not src.exists():
            raise FileNotFoundError(
                f"{src} missing — run the analysis scripts first"
            )
        dst = DST / dst_name
        shutil.copyfile(src, dst)
        written.append(dst)
    return written


if __name__ == "__main__":
    for path in export():
        print(f"exported {path} ({path.stat().st_size} bytes)")
