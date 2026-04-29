#!/usr/bin/env python3
"""OpenEvolve evaluator for Stage 2 MoP policy search.

This evaluator keeps the scientific boundary fixed:

- L2C expert pair: MLOP + SPP+PPF
- primary comparator: pair-best constituent single
- secondary comparator: no-prefetch
- heldout traces are never used here

The evolved program may only define a literal `candidate_policy()` dictionary
inside the evolve block. Parser, metric, split, and figure code stay frozen.
"""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openevolve.evaluation_result import EvaluationResult


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_ROOT = REPO_ROOT / "results" / "stage2_openevolve"
LEDGER_PATH = REPO_ROOT / "stage2" / "openevolve" / "candidate_ledger.jsonl"

EXPERT_0 = "MLOP"
EXPERT_1 = "SPP+PPF"
ALLOWED_ROUTERS = {"MoP-V1.1", "MoP-V1.2"}
ALLOWED_KEYS = {
    "router",
    "mop_total_budget",
    "mop_one_shot_epochs",
    "mop_accuracy_floor",
    "mop_guarded_min_budget_share",
    "mop_score_weights",
}
SMOKE_TRACES = ["429.mcf-192B"]
STAGE1_TRACES = ["429.mcf-192B", "450.soplex-92B", "parsec_2.1.fluidanimate.simlarge.prebuilt.drop_9500M.length_250M"]
STAGE2_TRACES = [
    "429.mcf-192B",
    "450.soplex-92B",
    "parsec_2.1.fluidanimate.simlarge.prebuilt.drop_9500M.length_250M",
    "parsec_2.1.raytrace.simlarge.prebuilt.drop_23500M.length_250M",
    "secret_compute_fp_45",
]
FROZEN_SPLIT_PATH = REPO_ROOT / "data" / "splits" / "official_v1.json"
EVOLVE_START = "# EVOLVE-BLOCK-START"
EVOLVE_END = "# EVOLVE-BLOCK-END"
CACHE_INPUTS = [
    Path(__file__).relative_to(REPO_ROOT),
    Path("scripts/run_mop_lite.py"),
    Path("scripts/run_single_prefetcher_baselines.py"),
    Path("configs/trace_suites.json"),
    Path("data/splits/official_v1.json"),
]


def geomean(values: list[float]) -> float:
    assert values
    assert min(values) > 0
    return math.exp(sum(math.log(v) for v in values) / len(values))


def extract_evolve_block(program_path: str) -> str:
    text = Path(program_path).read_text()
    assert EVOLVE_START in text and EVOLVE_END in text, "Candidate must keep evolve block markers"
    start = text.index(EVOLVE_START) + len(EVOLVE_START)
    end = text.index(EVOLVE_END)
    assert start < end, "Malformed evolve block"
    return text[start:end]


def literal_policy_from_function(fn: ast.FunctionDef) -> dict[str, Any]:
    assert fn.name == "candidate_policy", "Evolve block must define candidate_policy()"
    assert not fn.args.args and not fn.args.kwonlyargs and not fn.args.vararg and not fn.args.kwarg
    body = list(fn.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        assert isinstance(body[0].value.value, str), "Only a docstring may precede the return"
        body = body[1:]
    assert len(body) == 1 and isinstance(body[0], ast.Return), (
        "candidate_policy() must contain exactly one literal return"
    )
    return ast.literal_eval(body[0].value)


def load_policy_from_program(program_path: str) -> dict[str, Any]:
    tree = ast.parse(extract_evolve_block(program_path), filename=program_path)
    body = list(tree.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        assert isinstance(body[0].value.value, str), "Only a module docstring may precede candidate_policy()"
        body = body[1:]
    assert len(body) == 1 and isinstance(body[0], ast.FunctionDef), (
        "Evolve block may contain only candidate_policy(); imports, IO, and helper code are disallowed"
    )
    return literal_policy_from_function(body[0])


def validate_policy(raw: Any) -> dict[str, Any]:
    assert isinstance(raw, dict), "get_policy_config() must return a dict"
    unknown = sorted(set(raw) - ALLOWED_KEYS)
    assert not unknown, f"Unknown policy keys: {unknown}"
    missing = {"router", "mop_total_budget"} - set(raw)
    assert not missing, f"Missing policy keys: {sorted(missing)}"
    router = raw["router"]
    assert router in ALLOWED_ROUTERS, f"router must be one of {sorted(ALLOWED_ROUTERS)}"

    policy = dict(raw)
    policy["mop_total_budget"] = int(policy["mop_total_budget"])
    assert 512 <= policy["mop_total_budget"] <= 16384, "mop_total_budget out of allowed range"
    if "mop_one_shot_epochs" in policy:
        policy["mop_one_shot_epochs"] = int(policy["mop_one_shot_epochs"])
        assert 1 <= policy["mop_one_shot_epochs"] <= 8
    if "mop_accuracy_floor" in policy:
        policy["mop_accuracy_floor"] = int(policy["mop_accuracy_floor"])
        assert 0 <= policy["mop_accuracy_floor"] <= 95
    if "mop_guarded_min_budget_share" in policy:
        policy["mop_guarded_min_budget_share"] = int(policy["mop_guarded_min_budget_share"])
        assert 0 <= policy["mop_guarded_min_budget_share"] <= 50
    if "mop_score_weights" in policy:
        weights = [float(x) for x in policy["mop_score_weights"]]
        assert len(weights) == 3
        assert all(0.0 <= x <= 8.0 for x in weights)
        policy["mop_score_weights"] = weights
    return policy


def policy_hash(program_path: str, policy: dict[str, Any]) -> str:
    h = hashlib.sha256()
    h.update(Path(program_path).read_bytes())
    h.update(json.dumps(policy, sort_keys=True).encode())
    for rel_path in CACHE_INPUTS:
        path = REPO_ROOT / rel_path
        assert path.exists(), f"Cache input missing: {rel_path}"
        h.update(str(rel_path).encode())
        h.update(path.read_bytes())
    return h.hexdigest()[:16]


def repo_relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def stage_settings(stage: str) -> tuple[list[str], int, int]:
    if stage == "stage0":
        return SMOKE_TRACES, 100_000, 600_000
    if stage == "stage1":
        return STAGE1_TRACES, 500_000, 1_000_000
    if stage == "stage2":
        return STAGE2_TRACES, 500_000, 1_000_000
    raise AssertionError(f"Unknown STAGE2_EVAL_STAGE={stage!r}")


def assert_train_only(traces: list[str]) -> None:
    split = json.loads(FROZEN_SPLIT_PATH.read_text())["trace_sets"]
    train = set(split["train"])
    search_subset = set(split["search_subset"])
    heldout = set(split["heldout"])
    trace_set = set(traces)
    assert not trace_set & heldout, f"Stage 2 evaluator touched heldout traces: {sorted(trace_set & heldout)}"
    assert trace_set <= train, f"Stage 2 evaluator traces outside frozen train split: {sorted(trace_set - train)}"
    assert trace_set <= search_subset, (
        f"Stage 2 evaluator traces outside frozen search subset: {sorted(trace_set - search_subset)}"
    )


def policy_flags(policy: dict[str, Any]) -> list[str]:
    flags = ["--router", str(policy["router"]), "--mop-total-budget", str(policy["mop_total_budget"])]
    optional = [
        ("mop_one_shot_epochs", "--mop-one-shot-epochs"),
        ("mop_accuracy_floor", "--mop-accuracy-floor"),
        ("mop_guarded_min_budget_share", "--mop-guarded-min-budget-share"),
    ]
    for key, flag in optional:
        if key in policy:
            flags.extend([flag, str(policy[key])])
    if "mop_score_weights" in policy:
        flags.extend(["--mop-score-weights", ",".join(f"{x:g}" for x in policy["mop_score_weights"])])
    return flags


def run_candidate(policy: dict[str, Any], code_hash: str, stage: str) -> Path:
    traces, warmup, sim = stage_settings(stage)
    assert_train_only(traces)
    result_dir = RESULTS_ROOT / stage / code_hash
    if (result_dir / "summary.csv").exists() and os.environ.get("STAGE2_FORCE_RERUN") != "1":
        return result_dir
    result_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "scripts/run_mop_lite.py",
        "--expert-0",
        EXPERT_0,
        "--expert-1",
        EXPERT_1,
        "--warmup-instructions",
        str(warmup),
        "--simulation-instructions",
        str(sim),
        "--workers",
        "1",
        "--skip-download",
        "--epoch-trace",
        "--results-dir",
        str(result_dir),
    ]
    for trace in traces:
        cmd.extend(["--trace", trace])
    cmd.extend(policy_flags(policy))
    subprocess.run(cmd, cwd=REPO_ROOT, check=True, timeout=int(os.environ.get("STAGE2_SIM_TIMEOUT", "900")))
    return result_dir


def summarize_result(result_dir: Path, router: str) -> dict[str, float]:
    rows = list(csv.DictReader((result_dir / "summary.csv").open()))
    by_trace: dict[str, dict[str, dict[str, str]]] = {}
    for row in rows:
        by_trace.setdefault(row["trace"], {})[row["experiment"]] = row
    ratios_best = []
    ratios_base = []
    ratios_weaker = []
    catastrophic = 0
    beats_weaker = 0
    both_routees_gt_1 = 0
    for trace, trace_rows in sorted(by_trace.items()):
        assert router in trace_rows, f"Missing router row for {trace}/{router}"
        r = float(trace_rows[router]["speedup_vs_baseline"])
        e0 = float(trace_rows[EXPERT_0]["speedup_vs_baseline"])
        e1 = float(trace_rows[EXPERT_1]["speedup_vs_baseline"])
        pair_best = max(e0, e1)
        pair_weak = min(e0, e1)
        ratios_base.append(r)
        ratios_best.append(r / pair_best)
        ratios_weaker.append(r / pair_weak)
        catastrophic += (r / pair_best) < 0.95
        beats_weaker += r > pair_weak
        both_routees_gt_1 += e0 > 1.0 and e1 > 1.0
    action_rates = action_mix(result_dir, router)
    return {
        "n_traces": float(len(by_trace)),
        "gm_vs_pair_best": geomean(ratios_best),
        "gm_vs_nopref": geomean(ratios_base),
        "gm_vs_weaker": geomean(ratios_weaker),
        "beats_weaker_rate": beats_weaker / len(by_trace),
        "catastrophic_rate": catastrophic / len(by_trace),
        "both_routees_gt_1_rate": both_routees_gt_1 / len(by_trace),
        **action_rates,
    }


def action_mix(result_dir: Path, router: str) -> dict[str, float]:
    counts = {0: 0, 1: 0, 2: 0, 3: 0}
    total = 0
    for path in (result_dir / "runs").glob(f"*/epoch_logs/*__{router}.core0.csv"):
        for row in csv.DictReader(path.open()):
            counts[int(row["action"])] += 1
            total += 1
    if total == 0:
        return {"off_rate": 0.0, "both_on_rate": 0.0, "single_action_rate": 0.0}
    return {
        "off_rate": counts[0] / total,
        "both_on_rate": counts[3] / total,
        "single_action_rate": (counts[1] + counts[2]) / total,
    }


def fitness(metrics: dict[str, float]) -> float:
    score = math.log(metrics["gm_vs_pair_best"])
    score += 0.25 * math.log(metrics["gm_vs_nopref"])
    score += 0.20 * math.log(metrics["gm_vs_weaker"])
    score -= 0.12 * metrics["catastrophic_rate"]
    score -= 0.03 * metrics["off_rate"]
    return score


def append_ledger(record: dict[str, Any]) -> None:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER_PATH.open("a") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def evaluate(program_path: str) -> EvaluationResult:
    stage = os.environ.get("STAGE2_EVAL_STAGE", "stage0")
    try:
        policy = validate_policy(load_policy_from_program(program_path))
        code_hash = policy_hash(program_path, policy)
        result_dir = run_candidate(policy, code_hash, stage)
        metrics = summarize_result(result_dir, policy["router"])
        metrics["combined_score"] = fitness(metrics)
        metrics["stage_passed"] = 1.0
        record = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "stage": stage,
            "code_hash": code_hash,
            "policy": policy,
            "metrics": metrics,
            "result_dir": repo_relative(result_dir),
        }
        append_ledger(record)
        return EvaluationResult(
            metrics=metrics,
            artifacts={
                "result_dir": repo_relative(result_dir),
                "policy": json.dumps(policy, sort_keys=True),
                "summary": json.dumps(metrics, sort_keys=True),
            },
        )
    except Exception as exc:
        append_ledger({
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "stage": stage,
            "error": str(exc),
            "program_path": program_path,
        })
        return EvaluationResult(
            metrics={
                "combined_score": -10.0,
                "stage_passed": 0.0,
                "gm_vs_pair_best": 0.0,
                "gm_vs_nopref": 0.0,
                "gm_vs_weaker": 0.0,
            },
            artifacts={"error": str(exc)},
        )


def evaluate_stage1(program_path: str) -> EvaluationResult:
    return evaluate(program_path)
