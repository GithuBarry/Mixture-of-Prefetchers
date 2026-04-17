#!/usr/bin/env python3
"""Run the MoP-lite evaluation matrix on Athena (two-expert L2 coordinator).

Produces, under results/mop_lite/:
  logs/<trace>__<experiment>.{out,err}   raw simulator stdout/stderr
  metrics/<trace>__<experiment>.json     parsed metric key/value dictionary
  epoch_logs/<trace>__<experiment>.csv   per-epoch MoP trace (when requested)
  manifest.jsonl                         one JSON record per run (append-only)
  summary.csv / summary.md               human-readable roll-up

This script fails loud on missing traces / missing metrics / unknown experiments.
It never silently falls back to a default router or config; every run's exact
flags, seed, and revision are stamped in the manifest.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import shlex
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

from run_single_prefetcher_baselines import (
    DEFAULT_WORKERS,
    build_athena_if_needed,
    download_trace,
    load_athena_config,
    metric_float,
    normalize_trace_path,
    repo_root,
    replace_flag_value,
    run_one,
    shell_safe_trace_path,
)


EXPERTS = {
    "Pythia":  {"type": "scooby",       "config": "config/pythia.ini"},
    "SPP+PPF": {"type": "spp_ppf_dev",  "config": "config/spp_ppf_dev.ini"},
    "MLOP":    {"type": "mlop",         "config": "config/mlop.ini"},
    "SMS":     {"type": "sms",          "config": "config/sms.ini"},
}

# router name -> mop_router_type id in external/athena/inc/knobs.def
ROUTERS = {
    "FixedSplit":    0,
    "WinnerTakeAll": 1,
    "RandomRouter":  2,
    "OneShotFit":    3,
    "MoPLite":       4,
}

# Builtin multi-expert coordinators that pre-date MoP-lite; used as baselines.
BUILTIN_COORDINATORS = {
    "AthenaMAB": "config/mop_lite_mab.ini",
}

INTERESTING_CONFIG_KEYS = {
    "og_instr_epoch_len",
    "mop_total_budget",
    "mop_accuracy_floor",
    "mop_fixed_split_ratio",
    "mop_score_weights",
    "mop_seed",
    "mop_router_type",
    "mab_enable",
}


@dataclass(frozen=True)
class MopResult:
    trace: str
    experiment: str
    experiment_kind: str          # "baseline" | "single" | "router" | "builtin"
    ipc: float
    l2c_prefetch_issued_raw: float
    l2c_prefetch_issued: float
    l2c_prefetch_useful: float
    l2c_prefetch_useless: float
    l2c_prefetch_late: float
    l2c_load_miss: float
    l2c_mpki: float
    llc_load_miss: float
    downstream_prefetch_useful: float
    downstream_prefetch_accuracy: float
    pref0_issued_total: float
    pref1_issued_total: float
    pref0_useful_total: float
    pref1_useful_total: float
    pref0_budget_total: float
    pref1_budget_total: float
    pref0_selected_epochs: float
    pref1_selected_epochs: float
    log_path: Path
    metrics_path: Path


@dataclass(frozen=True)
class PlannedRun:
    trace: str
    experiment: str
    kind: str
    flags: str
    trace_path: Path
    epoch_trace_prefix: Path | None


def git_revision(root: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except subprocess.CalledProcessError:
        return "unknown"


def parse_simple_config(path: Path) -> dict[str, str]:
    settings: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in INTERESTING_CONFIG_KEYS:
            settings[key] = value.strip()
    return settings


def active_settings_from_flags(flags: str) -> dict[str, str]:
    settings: dict[str, str] = {}
    tokens = shlex.split(flags)
    for token in tokens:
        if token.startswith("--config="):
            cfg_path = Path(token.split("=", 1)[1])
            if cfg_path.exists():
                settings.update(parse_simple_config(cfg_path))
    for token in tokens:
        if not token.startswith("--") or "=" not in token:
            continue
        key, value = token[2:].split("=", 1)
        if key in INTERESTING_CONFIG_KEYS:
            settings[key] = value
    return settings


def build_base_flags(config_module, athena_home: Path, warmup: int, sim: int) -> str:
    flags = config_module.EXP_VARIABLES["BASE"]
    flags = replace_flag_value(flags, "--warmup_instructions", warmup)
    flags = replace_flag_value(flags, "--simulation_instructions", sim)
    return flags.replace("$(ATHENA_HOME)", shlex.quote(str(athena_home)))


def single_expert_flags(config_module, athena_home: Path, warmup: int, sim: int, expert: str) -> str:
    base = build_base_flags(config_module, athena_home, warmup, sim)
    spec = EXPERTS[expert]
    return (
        f"{base} "
        f"--l2c_prefetcher_types={spec['type']} "
        f"--config={shlex.quote(str(athena_home / spec['config']))} "
        "--l2c_prefetcher_force_prefetch_at_llc=true"
    )


def mop_flags(
    config_module,
    athena_home: Path,
    warmup: int,
    sim: int,
    expert0: str,
    expert1: str,
    router: str,
    seed: int,
    epoch_trace_prefix: Path | None,
) -> str:
    base = build_base_flags(config_module, athena_home, warmup, sim)
    spec0 = EXPERTS[expert0]
    spec1 = EXPERTS[expert1]
    flags = (
        f"{base} "
        f"--config={shlex.quote(str(athena_home / 'config' / 'mop_lite.ini'))} "
        f"--mop_router_type={ROUTERS[router]} "
        f"--mop_seed={seed} "
        f"--l2c_prefetcher_types={spec0['type']} "
        f"--config={shlex.quote(str(athena_home / spec0['config']))} "
        f"--l2c_prefetcher_types={spec1['type']} "
        f"--config={shlex.quote(str(athena_home / spec1['config']))} "
        "--l2c_prefetcher_force_prefetch_at_llc=true"
    )
    if epoch_trace_prefix is not None:
        flags += f" --mop_epoch_trace={shlex.quote(str(epoch_trace_prefix))}"
    return flags


def builtin_flags(
    config_module,
    athena_home: Path,
    warmup: int,
    sim: int,
    expert0: str,
    expert1: str,
    coordinator: str,
) -> str:
    base = build_base_flags(config_module, athena_home, warmup, sim)
    spec0 = EXPERTS[expert0]
    spec1 = EXPERTS[expert1]
    cfg = BUILTIN_COORDINATORS[coordinator]
    return (
        f"{base} "
        f"--config={shlex.quote(str(athena_home / cfg))} "
        f"--l2c_prefetcher_types={spec0['type']} "
        f"--config={shlex.quote(str(athena_home / spec0['config']))} "
        f"--l2c_prefetcher_types={spec1['type']} "
        f"--config={shlex.quote(str(athena_home / spec1['config']))} "
        "--l2c_prefetcher_force_prefetch_at_llc=true"
    )


def collect_result(trace: str, experiment: str, kind: str, run_result) -> MopResult:
    metrics = json.loads(run_result.metrics_path.read_text())
    l2c_load_miss = metric_float(metrics, "Core_0_L2C_load_miss")
    total_instructions = metric_float(metrics, "Core_0_total_instructions")
    l2c_mpki = 1000.0 * l2c_load_miss / total_instructions if total_instructions else 0.0
    l2c_prefetch_issued_effective = run_result.l2c_prefetch_issued
    downstream_prefetch_useful = (
        metric_float(metrics, "Core_0_L2C_prefetch_useful", default=0.0)
        + metric_float(metrics, "Core_0_LLC_prefetch_useful", default=0.0)
    )
    downstream_prefetch_accuracy = 0.0
    if l2c_prefetch_issued_effective:
        downstream_prefetch_accuracy = downstream_prefetch_useful / l2c_prefetch_issued_effective
    return MopResult(
        trace=trace,
        experiment=experiment,
        experiment_kind=kind,
        ipc=run_result.ipc,
        l2c_prefetch_issued_raw=run_result.l2c_prefetch_issued,
        l2c_prefetch_issued=l2c_prefetch_issued_effective,
        l2c_prefetch_useful=metric_float(metrics, "Core_0_L2C_prefetch_useful", default=0.0),
        l2c_prefetch_useless=metric_float(metrics, "Core_0_L2C_prefetch_useless", default=0.0),
        l2c_prefetch_late=metric_float(metrics, "Core_0_L2C_prefetch_late", default=0.0),
        l2c_load_miss=l2c_load_miss,
        l2c_mpki=l2c_mpki,
        llc_load_miss=metric_float(metrics, "Core_0_LLC_load_miss", default=0.0),
        downstream_prefetch_useful=downstream_prefetch_useful,
        downstream_prefetch_accuracy=downstream_prefetch_accuracy,
        pref0_issued_total=metric_float(metrics, "Core_0_mop_pref_0_issued_total", default=0.0),
        pref1_issued_total=metric_float(metrics, "Core_0_mop_pref_1_issued_total", default=0.0),
        pref0_useful_total=metric_float(metrics, "Core_0_mop_pref_0_useful_total", default=0.0),
        pref1_useful_total=metric_float(metrics, "Core_0_mop_pref_1_useful_total", default=0.0),
        pref0_budget_total=metric_float(metrics, "Core_0_mop_pref_0_budget_total", default=0.0),
        pref1_budget_total=metric_float(metrics, "Core_0_mop_pref_1_budget_total", default=0.0),
        pref0_selected_epochs=metric_float(metrics, "Core_0_mop_pref_0_selected_epochs", default=0.0),
        pref1_selected_epochs=metric_float(metrics, "Core_0_mop_pref_1_selected_epochs", default=0.0),
        log_path=run_result.log_path,
        metrics_path=run_result.metrics_path,
    )


def write_manifest_row(manifest_path: Path, record: dict) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("a") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def write_summary(results: list[MopResult], output_dir: Path, expert0: str, expert1: str) -> None:
    summary_csv = output_dir / "summary.csv"
    summary_md = output_dir / "summary.md"
    by_trace: dict[str, list[MopResult]] = {}
    for result in results:
        by_trace.setdefault(result.trace, []).append(result)

    header = [
        "trace", "experiment", "experiment_kind",
        "ipc", "speedup_vs_baseline", "speedup_vs_best_single",
        "l2c_load_miss", "l2c_mpki",
        "l2c_prefetch_issued_raw", "l2c_prefetch_issued", "l2c_prefetch_useful", "l2c_prefetch_useless", "l2c_prefetch_late",
        "downstream_prefetch_useful", "downstream_prefetch_accuracy",
        "pref0_issued_total", "pref1_issued_total",
        "pref0_useful_total", "pref1_useful_total",
        "pref0_budget_total", "pref1_budget_total",
        "pref0_selected_epochs", "pref1_selected_epochs",
        "log", "metrics",
    ]
    with summary_csv.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for trace in sorted(by_trace):
            trace_results = by_trace[trace]
            baseline = next(item for item in trace_results if item.experiment == "Baseline")
            single_results = [item for item in trace_results if item.experiment in {expert0, expert1}]
            best_single = max(single_results, key=lambda r: r.ipc) if single_results else baseline
            for item in sorted(trace_results, key=lambda r: (r.experiment_kind, r.experiment)):
                writer.writerow([
                    item.trace, item.experiment, item.experiment_kind,
                    f"{item.ipc:.6f}",
                    f"{item.ipc / baseline.ipc:.6f}",
                    f"{item.ipc / best_single.ipc:.6f}" if best_single.ipc else "",
                    f"{item.l2c_load_miss:.0f}",
                    f"{item.l2c_mpki:.6f}",
                    f"{item.l2c_prefetch_issued_raw:.0f}",
                    f"{item.l2c_prefetch_issued:.0f}",
                    f"{item.l2c_prefetch_useful:.0f}",
                    f"{item.l2c_prefetch_useless:.0f}",
                    f"{item.l2c_prefetch_late:.0f}",
                    f"{item.downstream_prefetch_useful:.0f}",
                    f"{item.downstream_prefetch_accuracy:.6f}",
                    f"{item.pref0_issued_total:.0f}",
                    f"{item.pref1_issued_total:.0f}",
                    f"{item.pref0_useful_total:.0f}",
                    f"{item.pref1_useful_total:.0f}",
                    f"{item.pref0_budget_total:.0f}",
                    f"{item.pref1_budget_total:.0f}",
                    f"{item.pref0_selected_epochs:.0f}",
                    f"{item.pref1_selected_epochs:.0f}",
                    item.log_path, item.metrics_path,
                ])

    lines = [
        f"# MoP-lite Evaluation ({expert0} + {expert1})",
        "",
        "| Trace | Baseline IPC | Best single | Best coord | Coord IPC | Speedup vs best single |",
        "| --- | ---: | --- | --- | ---: | ---: |",
    ]
    for trace in sorted(by_trace):
        trace_results = by_trace[trace]
        baseline = next(item for item in trace_results if item.experiment == "Baseline")
        single_results = [r for r in trace_results if r.experiment in {expert0, expert1}]
        coord_results = [r for r in trace_results if r.experiment_kind in {"router", "builtin"}]
        if not single_results or not coord_results:
            continue
        best_single = max(single_results, key=lambda r: r.ipc)
        best_coord = max(coord_results, key=lambda r: r.ipc)
        lines.append(
            f"| {trace} | {baseline.ipc:.4f} | {best_single.experiment} | "
            f"{best_coord.experiment} | {best_coord.ipc:.4f} | "
            f"{best_coord.ipc / best_single.ipc:.4f}x |"
        )
    summary_md.write_text("\n".join(lines) + "\n")


def load_run_mode(root: Path, mode: str) -> dict:
    modes = json.loads((root / "configs" / "run_modes.json").read_text())
    assert mode in modes["run_modes"], f"Unknown run mode '{mode}'. Options: {list(modes['run_modes'])}"
    return modes["run_modes"][mode]


def load_trace_suite(root: Path, set_name: str) -> list[str]:
    suites = json.loads((root / "configs" / "trace_suites.json").read_text())
    assert set_name in suites["trace_sets"], f"Unknown trace set '{set_name}'"
    return suites["trace_sets"][set_name]


def resolve_routers(root: Path, spec) -> list[str]:
    if isinstance(spec, list):
        for name in spec:
            assert name in ROUTERS, f"Unknown router '{name}'"
        return list(spec)
    suites = json.loads((root / "configs" / "trace_suites.json").read_text())
    assert spec in suites, f"Router alias '{spec}' not found in trace_suites.json"
    return list(suites[spec])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["smoke_mode", "search_mode", "final_mode"],
                        help="Named run mode from configs/run_modes.json. Supplies defaults for omitted options.")
    parser.add_argument("--trace", dest="traces", action="append")
    parser.add_argument("--expert-0", choices=sorted(EXPERTS), default=None)
    parser.add_argument("--expert-1", choices=sorted(EXPERTS), default=None)
    parser.add_argument("--router", dest="routers", action="append", choices=sorted(ROUTERS))
    parser.add_argument("--builtin", dest="builtins", action="append", choices=sorted(BUILTIN_COORDINATORS))
    parser.add_argument("--single-baseline", dest="single_baselines", action="append",
                        choices=sorted(EXPERTS),
                        help="Additional single-prefetcher baselines beyond expert-0 / expert-1.")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--warmup-instructions", type=int, default=None)
    parser.add_argument("--simulation-instructions", type=int, default=None)
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help="Maximum concurrent simulator processes (default: 8). Use 1 for serial execution.",
    )
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument("--epoch-trace", action="store_true")
    parser.add_argument("--results-dir", type=Path, default=None,
                        help="Override output directory (default results/mop_lite).")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    assert args.workers > 0, "--workers must be >= 1"

    root = repo_root()
    athena_home = root / "external" / "athena"
    traces_dir = root / "artifacts" / "athena_traces"

    # Resolve run_mode settings first so CLI flags override cleanly.
    traces = args.traces
    routers = args.routers
    builtins = args.builtins or []
    single_baselines = args.single_baselines
    warmup = args.warmup_instructions
    sim = args.simulation_instructions
    expert_0 = args.expert_0
    expert_1 = args.expert_1

    if args.mode:
        mode = load_run_mode(root, args.mode)
        traces = traces or load_trace_suite(root, mode["trace_set"])
        routers = routers or resolve_routers(root, mode["mop_lite"]["routers"])
        builtins = args.builtins or mode.get("builtin_coordinators", [])
        # single_prefetcher_baselines may include Baseline + experts; strip duplicates later.
        requested_singles = mode.get("single_prefetcher_baselines", {}).get("experiments", [])
        mode_singles = [s for s in requested_singles if s in EXPERTS]
        single_baselines = single_baselines or mode_singles
        warmup = warmup or mode["warmup_instructions"]
        sim = sim or mode["simulation_instructions"]
        expert_0 = expert_0 or mode["mop_lite"].get("expert_0")
        expert_1 = expert_1 or mode["mop_lite"].get("expert_1")

    warmup = warmup or 5_000_000
    sim = sim or 10_000_000
    expert_0 = expert_0 or "Pythia"
    expert_1 = expert_1 or "SPP+PPF"
    routers = routers or []
    builtins = builtins or []

    assert expert_0 != expert_1, "Choose two distinct experts"

    assert traces, "No traces selected. Use --trace or --mode."

    # Default single baselines = the two experts themselves (so we always have both
    # reference points for speedup_vs_best_single).
    extra_singles = set(single_baselines or [])
    extra_singles.update({expert_0, expert_1})

    output_dir = args.results_dir or (root / "results" / "mop_lite")
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.jsonl"

    config_module = load_athena_config(athena_home)

    trace_info = {}
    for trace_name in traces:
        assert trace_name in config_module.TRACE_DATA, f"Unknown Athena trace: {trace_name}"
        trace_info[trace_name] = config_module.get_trace_info(trace_name)

    local_trace_paths = {}
    for trace_name, info in trace_info.items():
        local_path = traces_dir / normalize_trace_path(info["path"])
        if local_path.exists():
            local_trace_paths[trace_name] = local_path
            continue
        assert not args.skip_download, f"Missing trace {local_path}; rerun without --skip-download"
        local_trace_paths[trace_name] = download_trace(trace_name, info, traces_dir)

    if args.download_only:
        for trace_name, path in local_trace_paths.items():
            print(f"{trace_name}: {path}")
        return 0

    binary = build_athena_if_needed(athena_home)
    safe_trace_paths = {
        trace_name: shell_safe_trace_path(path)
        for trace_name, path in local_trace_paths.items()
    }
    revision = git_revision(root)
    hostname = socket.gethostname()

    # Assemble experiment list.
    experiment_plan: list[tuple[str, str]] = [("Baseline", "baseline")]
    for expert in sorted(extra_singles):
        experiment_plan.append((expert, "single"))
    for router in routers:
        experiment_plan.append((router, "router"))
    for coord in builtins:
        experiment_plan.append((coord, "builtin"))

    planned_runs: list[PlannedRun] = []
    for trace_name in traces:
        for experiment, kind in experiment_plan:
            epoch_trace_prefix: Path | None = None
            if kind == "baseline":
                flags = build_base_flags(config_module, athena_home, warmup, sim)
            elif kind == "single":
                flags = single_expert_flags(config_module, athena_home, warmup, sim, experiment)
            elif kind == "router":
                if args.epoch_trace:
                    epoch_trace_prefix = output_dir / "epoch_logs" / f"{trace_name}__{experiment}"
                    epoch_trace_prefix.parent.mkdir(parents=True, exist_ok=True)
                flags = mop_flags(
                    config_module, athena_home, warmup, sim,
                    expert_0, expert_1, experiment, args.seed, epoch_trace_prefix,
                )
            elif kind == "builtin":
                flags = builtin_flags(
                    config_module, athena_home, warmup, sim,
                    expert_0, expert_1, experiment,
                )
            else:
                raise AssertionError(f"Unknown experiment kind: {kind}")

            planned_runs.append(
                PlannedRun(
                    trace=trace_name,
                    experiment=experiment,
                    kind=kind,
                    flags=flags,
                    trace_path=safe_trace_paths[trace_name],
                    epoch_trace_prefix=epoch_trace_prefix,
                )
            )

    def execute_planned_run(plan: PlannedRun):
        start = datetime.now(timezone.utc)
        run_result = run_one(
            binary=binary,
            athena_home=athena_home,
            flags=plan.flags,
            trace_path=plan.trace_path,
            trace_name=plan.trace,
            experiment=plan.experiment,
            output_dir=output_dir,
        )
        end = datetime.now(timezone.utc)
        return run_result, start, end

    results: list[MopResult] = []
    print(
        f"Launching {len(planned_runs)} runs with up to {args.workers} workers",
        flush=True,
    )
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_plan = {}
        for plan in planned_runs:
            print(f"Queueing {plan.trace} + {plan.experiment} [{plan.kind}]", flush=True)
            future = executor.submit(execute_planned_run, plan)
            future_to_plan[future] = plan

        for future in as_completed(future_to_plan):
            plan = future_to_plan[future]
            run_result, start, end = future.result()
            active_settings = active_settings_from_flags(plan.flags)
            result = collect_result(plan.trace, plan.experiment, plan.kind, run_result)
            results.append(result)
            print(f"Finished {plan.trace} + {plan.experiment} [{plan.kind}]", flush=True)

            manifest_record = {
                "trace": plan.trace,
                "experiment": plan.experiment,
                "experiment_kind": plan.kind,
                "expert_0": expert_0 if plan.kind in {"router", "builtin"} else None,
                "expert_1": expert_1 if plan.kind in {"router", "builtin"} else None,
                "router": plan.experiment if plan.kind == "router" else None,
                "builtin_coordinator": plan.experiment if plan.kind == "builtin" else None,
                "seed": int(active_settings["mop_seed"]) if "mop_seed" in active_settings else None,
                "warmup_instructions": warmup,
                "simulation_instructions": sim,
                "mode": args.mode,
                "epoch_len_instructions": int(active_settings["og_instr_epoch_len"]) if "og_instr_epoch_len" in active_settings else None,
                "mop_total_budget": int(active_settings["mop_total_budget"]) if "mop_total_budget" in active_settings else None,
                "mop_accuracy_floor": int(active_settings["mop_accuracy_floor"]) if "mop_accuracy_floor" in active_settings else None,
                "mop_fixed_split_ratio": int(active_settings["mop_fixed_split_ratio"]) if "mop_fixed_split_ratio" in active_settings else None,
                "mop_score_weights": active_settings.get("mop_score_weights"),
                "git_revision": revision,
                "host": hostname,
                "start_utc": start.isoformat(),
                "end_utc": end.isoformat(),
                "duration_s": (end - start).total_seconds(),
                "flags": plan.flags,
                "trace_path": str(local_trace_paths[plan.trace]),
                "log_path": str(run_result.log_path),
                "stderr_path": str(run_result.err_path),
                "metrics_path": str(run_result.metrics_path),
                "epoch_trace_prefix": str(plan.epoch_trace_prefix) if plan.epoch_trace_prefix else None,
                "ipc": result.ipc,
                "l2c_load_miss": result.l2c_load_miss,
                "l2c_mpki": result.l2c_mpki,
                "l2c_prefetch_issued_raw": result.l2c_prefetch_issued_raw,
                "l2c_prefetch_issued": result.l2c_prefetch_issued,
                "l2c_prefetch_useful": result.l2c_prefetch_useful,
                "l2c_prefetch_useless": result.l2c_prefetch_useless,
                "l2c_prefetch_late": result.l2c_prefetch_late,
                "downstream_prefetch_useful": result.downstream_prefetch_useful,
                "downstream_prefetch_accuracy": result.downstream_prefetch_accuracy,
                "pref0_issued_total": result.pref0_issued_total,
                "pref1_issued_total": result.pref1_issued_total,
                "pref0_useful_total": result.pref0_useful_total,
                "pref1_useful_total": result.pref1_useful_total,
                "pref0_budget_total": result.pref0_budget_total,
                "pref1_budget_total": result.pref1_budget_total,
                "pref0_selected_epochs": result.pref0_selected_epochs,
                "pref1_selected_epochs": result.pref1_selected_epochs,
            }
            write_manifest_row(manifest_path, manifest_record)

    write_summary(results, output_dir, expert_0, expert_1)
    print(f"Wrote {len(results)} runs to {output_dir}")
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
