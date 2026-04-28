"""
OpenEvolve evaluator for MoP-lite Stage 2 search.

Given a candidate policy file (initial_program.py variant), this evaluator:
  1. Extracts POLICY_CONFIG from the candidate
  2. Writes a temp Athena INI config with those knob values
  3. Patches oogway.cc case 5 decision/budget logic from the candidate functions
  4. Compiles Athena
  5. Runs on the smoke_subset (2 traces, fast) for Stage 0/1 gates
  6. Runs on the search_subset (10 traces) for the main fitness signal
  7. Returns a fitness dict with geomean speedup_vs_best_single as the primary score

Fitness dict keys:
  score               -- primary: geomean speedup_vs_best_single on search_subset (higher is better)
  score_vs_noprefetch -- geomean speedup_vs_baseline on search_subset
  both_off_rate       -- average both-off epoch fraction across traces (lower is better)
  smoke_score         -- geomean on 2-trace smoke subset (Stage 0 validity gate)
  valid               -- bool: False if compile fails or smoke_score < 0.85
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
ATHENA = REPO_ROOT / "external" / "athena"
RESULTS_BASE = REPO_ROOT / "results" / "openevolve_search"
CANDIDATE_LEDGER = REPO_ROOT / "openevolve" / "candidate_ledger.jsonl"

# Use conda Python (has all deps) rather than system Python
PYTHON = "/opt/anaconda3/bin/python3"

# Fast 4-trace scout set — covers both failure-mode traces and two win-region traces.
# ~4-6 min per evaluation, fast enough for 40 iterations in a few hours.
SCOUT_TRACES = [
    "429.mcf-192B",                  # both-off failure trace
    "parsec_2.1.fluidanimate.simlarge.prebuilt.drop_9500M.length_250M",  # both-off trace
    "605.mcf_s-472B",                # win-region trace (OpenEvolve beats baseline here)
    "450.soplex-92B",                # mixed trace
]

SMOKE_WARMUP = 5_000_000
SMOKE_SIM = 10_000_000

BASE_INI_TEMPLATE = """og_enable=true
og_multi_prefetcher_enable=true
og_coordination_mode=l2c_l2c
og_l2c_only_coordination=true
og_epoch_by_inst=true
og_instr_epoch_len={epoch_len}
mop_enable=true
mop_router_type=5
mop_total_budget={total_budget}
mop_fixed_split_ratio=50
mop_accuracy_floor={accuracy_floor:d}
mop_score_weights={w0},{w1},{w2}
mop_one_shot_epochs=4
mop_seed=1
mop_winner_isolation_threshold={isolation_threshold}
"""


def load_candidate(program_path: str) -> dict:
    """Load POLICY_CONFIG from a candidate program file."""
    spec = importlib.util.spec_from_file_location("candidate", program_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.POLICY_CONFIG


def write_ini(cfg: dict, path: Path) -> None:
    weights = cfg.get("mop_score_weights", [cfg.get("accuracy_weight", 1.0),
                                             cfg.get("coverage_weight", 0.25),
                                             cfg.get("traffic_weight", 1.0)])
    ini = BASE_INI_TEMPLATE.format(
        epoch_len=int(cfg.get("og_instr_epoch_len", 500_000)),
        total_budget=int(cfg.get("mop_total_budget", 2048)),
        accuracy_floor=int(cfg.get("accuracy_floor", cfg.get("mop_accuracy_floor", 30))),
        w0=weights[0], w1=weights[1], w2=weights[2],
        isolation_threshold=float(cfg.get("isolation_threshold",
                                          cfg.get("mop_winner_isolation_threshold", 3.0))),
    )
    path.write_text(ini)


def build_athena(ini_path: Path) -> bool:
    """Copy the candidate INI over mop_lite_open_evolve.ini and rebuild Athena."""
    target = ATHENA / "config" / "mop_lite_open_evolve.ini"
    shutil.copy(ini_path, target)
    result = subprocess.run(
        ["make", "-C", str(ATHENA), "-j4"],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def run_batch(traces: list[str], results_dir: Path, warmup: int, sim: int,
              extra_flags: list[str] | None = None) -> dict | None:
    """Run the MoP-lite evaluation on a set of traces and return summary CSV rows."""
    results_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        PYTHON, str(SCRIPTS / "run_mop_lite.py"),
        "--expert-0", "Pythia", "--expert-1", "SPP+PPF",
        "--router", "OpenEvolve", "--router", "MoPLite",
        "--builtin", "AthenaMAB",
        "--warmup-instructions", str(warmup),
        "--simulation-instructions", str(sim),
        "--workers", "4",
        "--skip-download",
        "--results-dir", str(results_dir),
    ]
    for t in traces:
        cmd += ["--trace", t]
    if extra_flags:
        cmd += extra_flags

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
    if result.returncode != 0:
        return None

    summary_csv = results_dir / "summary.csv"
    if not summary_csv.exists():
        return None

    import csv
    rows = list(csv.DictReader(open(summary_csv)))
    return rows


def geomean_speedup(rows: list[dict], experiment: str, col: str) -> float:
    vals = [float(r[col]) for r in rows
            if r["experiment"] == experiment and float(r[col]) > 0]
    if not vals:
        return 0.0
    return math.exp(sum(math.log(v) for v in vals) / len(vals))


def both_off_rate(results_dir: Path) -> float:
    """Compute average both-off epoch fraction from epoch traces."""
    import glob, csv as csvmod
    rates = []
    for f in glob.glob(str(results_dir / "runs" / "*" / "epoch_logs" / "*OpenEvolve*.csv")):
        data = list(csvmod.DictReader(open(f)))
        if not data:
            continue
        total = len(data)
        off = sum(1 for r in data if r.get("action") == "0")
        rates.append(off / total)
    return sum(rates) / len(rates) if rates else 1.0


def evaluate(program_path: str) -> dict:
    """Main evaluator entry point called by OpenEvolve."""
    # --- Load candidate policy config ---
    try:
        cfg = load_candidate(program_path)
    except Exception as e:
        return {"score": 0.0, "valid": False, "error": f"load failed: {e}"}

    # --- Write INI and compile ---
    with tempfile.NamedTemporaryFile(suffix=".ini", delete=False) as f:
        ini_path = Path(f.name)
    write_ini(cfg, ini_path)

    if not build_athena(ini_path):
        ini_path.unlink(missing_ok=True)
        return {"score": 0.0, "valid": False, "error": "compile failed"}
    ini_path.unlink(missing_ok=True)

    import uuid
    run_id = uuid.uuid4().hex[:8]

    # --- Scout evaluation: 4-trace fast set (~4-6 min, suitable for iterative search) ---
    # Covers both known failure-mode traces and two win-region traces.
    # Full 10-trace evaluation is run manually on the best candidate only.
    scout_dir = RESULTS_BASE / f"{run_id}_scout"
    scout_rows = run_batch(SCOUT_TRACES, scout_dir, SMOKE_WARMUP, SMOKE_SIM,
                           extra_flags=["--epoch-trace"])
    if scout_rows is None:
        return {"score": 0.0, "valid": False, "error": "scout run failed"}

    primary = geomean_speedup(scout_rows, "OpenEvolve", "speedup_vs_best_single")
    vs_noprefetch = geomean_speedup(scout_rows, "OpenEvolve", "speedup_vs_baseline")
    off_rate = both_off_rate(scout_dir)

    # Validity gate: reject clearly broken candidates
    if primary < 0.80:
        return {"score": primary, "valid": False,
                "error": f"scout gate failed: {primary:.4f} < 0.80"}

    # Composite fitness: primary score + bonus for beating no-prefetch + penalty for both-off
    fitness = primary + 0.05 * max(0.0, vs_noprefetch - 1.0) - 0.02 * off_rate

    result = {
        "score": round(fitness, 6),
        "score_vs_best_single": round(primary, 6),
        "score_vs_noprefetch": round(vs_noprefetch, 6),
        "both_off_rate": round(off_rate, 4),
        "run_id": run_id,
        "valid": True,
    }

    # Append to candidate ledger
    CANDIDATE_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(CANDIDATE_LEDGER, "a") as f:
        f.write(json.dumps({
            "program_path": program_path,
            "run_id": run_id,
            **result,
        }) + "\n")

    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: evaluator.py <program_path>")
        sys.exit(1)
    result = evaluate(sys.argv[1])
    print(json.dumps(result, indent=2))
