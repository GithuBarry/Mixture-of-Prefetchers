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
        raise ValueError(f"Unknown router reference: {key}")
    raise ValueError(f"Invalid routers spec: {spec!r}")


def trace_flags(traces: list[str]) -> str:
    return " ".join(f"--trace {json.dumps(t)}" for t in traces)


def router_flags(routers: list[str]) -> str:
    return " ".join(f"--router {json.dumps(r)}" for r in routers)


def llc_flags(prefetchers: list[str]) -> str:
    return " ".join(f"--llc-prefetcher {json.dumps(p)}" for p in prefetchers)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        nargs="?",
        default="search_mode",
        choices=["search_mode", "final_mode", "smoke_mode"],
        help="Run mode from configs/run_modes.json",
    )
    parser.add_argument(
        "--list-traces",
        action="store_true",
        help="Only print trace names for the mode's trace set (one per line).",
    )
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
    e0 = mode["mop_lite"]["expert_0"]
    e1 = mode["mop_lite"]["expert_1"]
    bl = " ".join(
        f"--experiment {json.dumps(e)}" for e in mode["single_prefetcher_baselines"]["experiments"]
    )
    llc = llc_flags(mode.get("llc_prefetcher_baselines", []))

    print("# Trace set:", set_name, f"({len(traces)} traces)")
    print("# From:", suites_path)
    print()
    print("# --- MoP-lite ---")
    print(
        "python3 scripts/run_mop_lite.py "
        f"--warmup-instructions {w} --simulation-instructions {s} "
        f"--expert-0 {json.dumps(e0)} --expert-1 {json.dumps(e1)} "
        f"{router_flags(routers)} "
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
