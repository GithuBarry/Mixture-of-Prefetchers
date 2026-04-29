#!/usr/bin/env python3
"""Print example shell commands for MoP-lite and baseline runners from configs/*.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def trace_list(suites: dict, set_name: str) -> list[str]:
    traces = suites["trace_sets"][set_name]
    if not isinstance(traces, list):
        raise ValueError(f"trace set {set_name} must be a list")
    return traces


def resolve_routers(suites: dict, mode: dict) -> list[str]:
    spec = mode["mop_lite"]["routers"]
    if isinstance(spec, list):
        return spec
    if isinstance(spec, str):
        key = spec
        if key == "recommended_routers_all":
            return list(suites["recommended_routers_all"])
        if key == "recommended_routers_search_fast":
            return list(suites["recommended_routers_search_fast"])
        if key == "stage1_candidate_routers":
            return list(suites["stage1_candidate_routers"])
        raise ValueError(f"Unknown router reference: {key}")
    raise ValueError(f"Invalid routers spec: {spec!r}")


def trace_flags(traces: list[str]) -> str:
    return " ".join(f"--trace {json.dumps(t)}" for t in traces)


def router_flags(routers: list[str]) -> str:
    return " ".join(f"--router {json.dumps(r)}" for r in routers)


def llc_flags(prefetchers: list[str]) -> str:
    return " ".join(f"--llc-prefetcher {json.dumps(p)}" for p in prefetchers)


def builtin_flags(coordinators: list[str]) -> str:
    return " ".join(f"--builtin {json.dumps(c)}" for c in coordinators)


def mop_knob_flags(knobs: dict) -> str:
    allowed = {
        "mop_total_budget": "--mop-total-budget",
        "mop_accuracy_floor": "--mop-accuracy-floor",
        "mop_guarded_min_budget_share": "--mop-guarded-min-budget-share",
        "mop_one_shot_epochs": "--mop-one-shot-epochs",
        "mop_score_weights": "--mop-score-weights",
    }
    unknown = sorted(set(knobs) - set(allowed))
    if unknown:
        raise ValueError(f"Unknown mop_knobs: {unknown}")
    parts = []
    for key in allowed:
        if key not in knobs:
            continue
        value = knobs[key]
        if key == "mop_score_weights":
            assert isinstance(value, list), "mop_score_weights must be a list"
            value = ",".join(str(float(x)) for x in value)
        else:
            value = str(int(value))
        parts.append(f"{allowed[key]} {json.dumps(value)}")
    return " ".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        nargs="?",
        default="search_mode",
        choices=[
            "search_mode",
            "final_mode",
            "smoke_mode",
            "stage1_pair_screen_1m",
            "stage1_pair_confirm_10m",
            "stage1_train_confirm_10m",
        ],
        help="Run mode from configs/run_modes.json",
    )
    parser.add_argument(
        "--list-traces",
        action="store_true",
        help="Only print trace names for the mode's trace set (one per line).",
    )
    parser.add_argument("--expert-0", help="Override the mode's first L2C routee expert.")
    parser.add_argument("--expert-1", help="Override the mode's second L2C routee expert.")
    args = parser.parse_args()

    root = repo_root()
    suites_path = root / "configs" / "trace_suites.json"
    modes_path = root / "configs" / "run_modes.json"
    suites = load_json(suites_path)
    modes_doc = load_json(modes_path)
    mode = modes_doc["run_modes"][args.mode]
    set_name = mode["trace_set"]
    traces = trace_list(suites, set_name)
    routers = resolve_routers(suites, mode)

    if args.list_traces:
        for t in traces:
            print(t)
        return 0

    w = mode["warmup_instructions"]
    s = mode["simulation_instructions"]
    e0 = args.expert_0 or mode["mop_lite"]["expert_0"]
    e1 = args.expert_1 or mode["mop_lite"]["expert_1"]
    bl = " ".join(
        f"--experiment {json.dumps(e)}" for e in mode["single_prefetcher_baselines"]["experiments"]
    )
    llc = llc_flags(mode.get("llc_prefetcher_baselines", []))
    builtins = builtin_flags(mode.get("builtin_coordinators", []))
    mop_knobs = mop_knob_flags(mode.get("mop_knobs", {}))

    print("# Trace set:", set_name, f"({len(traces)} traces)")
    print("# From:", suites_path)
    print()
    print("# --- MoP-lite ---")
    print(
        "python3 scripts/run_mop_lite.py "
        f"--warmup-instructions {w} --simulation-instructions {s} "
        f"--expert-0 {json.dumps(e0)} --expert-1 {json.dumps(e1)} "
        f"{router_flags(routers)} "
        f"{builtins} "
        f"{mop_knobs} "
        f"{llc} "
        f"{trace_flags(traces)}"
    )
    print()
    print("# --- Single-prefetcher baselines ---")
    print(
        "python3 scripts/run_single_prefetcher_baselines.py "
        f"--warmup-instructions {w} --simulation-instructions {s} "
        f"{bl} "
        f"{trace_flags(traces)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
