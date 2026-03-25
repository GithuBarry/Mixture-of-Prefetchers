#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shlex
from dataclasses import dataclass
from pathlib import Path

from run_single_prefetcher_baselines import (
    DEFAULT_TRACES,
    build_athena_if_needed,
    download_trace,
    load_athena_config,
    metric_float,
    normalize_trace_path,
    repo_root,
    replace_flag_value,
    run_one,
)


EXPERTS = {
    "Pythia": {"type": "scooby", "config": "config/pythia.ini"},
    "SPP+PPF": {"type": "spp_ppf_dev", "config": "config/spp_ppf_dev.ini"},
    "MLOP": {"type": "mlop", "config": "config/mlop.ini"},
    "SMS": {"type": "sms", "config": "config/sms.ini"},
}

ROUTERS = {
    "FixedSplit": 0,
    "WinnerTakeAll": 1,
    "RandomRouter": 2,
    "OneShotFit": 3,
    "MoPLite": 4,
}


@dataclass(frozen=True)
class MopResult:
    trace: str
    experiment: str
    ipc: float
    l2c_prefetch_issued: float
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
    epoch_trace_prefix: Path | None,
) -> str:
    base = build_base_flags(config_module, athena_home, warmup, sim)
    spec0 = EXPERTS[expert0]
    spec1 = EXPERTS[expert1]
    flags = (
        f"{base} "
        f"--config={shlex.quote(str(athena_home / 'config' / 'mop_lite.ini'))} "
        f"--mop_router_type={ROUTERS[router]} "
        f"--l2c_prefetcher_types={spec0['type']} "
        f"--config={shlex.quote(str(athena_home / spec0['config']))} "
        f"--l2c_prefetcher_types={spec1['type']} "
        f"--config={shlex.quote(str(athena_home / spec1['config']))} "
        "--l2c_prefetcher_force_prefetch_at_llc=true"
    )
    if epoch_trace_prefix is not None:
        flags += f" --mop_epoch_trace={shlex.quote(str(epoch_trace_prefix))}"
    return flags


def collect_result(trace: str, experiment: str, run_result) -> MopResult:
    metrics = json.loads(run_result.metrics_path.read_text())
    return MopResult(
        trace=trace,
        experiment=experiment,
        ipc=run_result.ipc,
        l2c_prefetch_issued=run_result.l2c_prefetch_issued,
        downstream_prefetch_useful=run_result.downstream_prefetch_useful,
        downstream_prefetch_accuracy=run_result.downstream_prefetch_accuracy,
        pref0_issued_total=metric_float(metrics, "Core_0_mop_pref_0_issued_total"),
        pref1_issued_total=metric_float(metrics, "Core_0_mop_pref_1_issued_total"),
        pref0_useful_total=metric_float(metrics, "Core_0_mop_pref_0_useful_total"),
        pref1_useful_total=metric_float(metrics, "Core_0_mop_pref_1_useful_total"),
        pref0_budget_total=metric_float(metrics, "Core_0_mop_pref_0_budget_total"),
        pref1_budget_total=metric_float(metrics, "Core_0_mop_pref_1_budget_total"),
        pref0_selected_epochs=metric_float(metrics, "Core_0_mop_pref_0_selected_epochs"),
        pref1_selected_epochs=metric_float(metrics, "Core_0_mop_pref_1_selected_epochs"),
        log_path=run_result.log_path,
        metrics_path=run_result.metrics_path,
    )


def write_summary(results: list[MopResult], output_dir: Path, expert0: str, expert1: str) -> None:
    summary_csv = output_dir / "summary.csv"
    summary_md = output_dir / "summary.md"
    by_trace: dict[str, list[MopResult]] = {}
    for result in results:
        by_trace.setdefault(result.trace, []).append(result)

    with summary_csv.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "trace",
                "experiment",
                "ipc",
                "speedup_vs_baseline",
                "speedup_vs_best_single",
                "l2c_prefetch_issued",
                "downstream_prefetch_useful",
                "downstream_prefetch_accuracy",
                "pref0_issued_total",
                "pref1_issued_total",
                "pref0_useful_total",
                "pref1_useful_total",
                "pref0_budget_total",
                "pref1_budget_total",
                "pref0_selected_epochs",
                "pref1_selected_epochs",
                "log",
                "metrics",
            ]
        )
        for trace in sorted(by_trace):
            trace_results = by_trace[trace]
            baseline = next(item for item in trace_results if item.experiment == "Baseline")
            best_single = max(
                (item for item in trace_results if item.experiment in {expert0, expert1}),
                key=lambda item: item.ipc,
            )
            for item in sorted(trace_results, key=lambda current: current.experiment):
                writer.writerow(
                    [
                        item.trace,
                        item.experiment,
                        f"{item.ipc:.6f}",
                        f"{item.ipc / baseline.ipc:.6f}",
                        f"{item.ipc / best_single.ipc:.6f}",
                        f"{item.l2c_prefetch_issued:.0f}",
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
                        item.log_path,
                        item.metrics_path,
                    ]
                )

    lines = [
        f"# MoP-lite Evaluation ({expert0} + {expert1})",
        "",
        "| Trace | Baseline IPC | Best single | Best router | Router IPC | Speedup vs Best single |",
        "| --- | ---: | --- | --- | ---: | ---: |",
    ]
    for trace in sorted(by_trace):
        trace_results = by_trace[trace]
        baseline = next(item for item in trace_results if item.experiment == "Baseline")
        best_single = max(
            (item for item in trace_results if item.experiment in {expert0, expert1}),
            key=lambda item: item.ipc,
        )
        best_router = max(
            (item for item in trace_results if item.experiment in ROUTERS),
            key=lambda item: item.ipc,
        )
        lines.append(
            f"| {trace} | {baseline.ipc:.4f} | {best_single.experiment} | {best_router.experiment} | {best_router.ipc:.4f} | {best_router.ipc / best_single.ipc:.4f}x |"
        )
    summary_md.write_text("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", dest="traces", action="append")
    parser.add_argument("--expert-0", choices=sorted(EXPERTS), default="Pythia")
    parser.add_argument("--expert-1", choices=sorted(EXPERTS), default="SPP+PPF")
    parser.add_argument("--router", dest="routers", action="append", choices=sorted(ROUTERS))
    parser.add_argument("--warmup-instructions", type=int, default=5_000_000)
    parser.add_argument("--simulation-instructions", type=int, default=10_000_000)
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument("--epoch-trace", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    assert args.expert_0 != args.expert_1, "Choose two distinct experts"

    root = repo_root()
    athena_home = root / "external" / "athena"
    traces_dir = root / "artifacts" / "athena_traces"
    output_dir = root / "results" / "mop_lite"
    output_dir.mkdir(parents=True, exist_ok=True)

    config_module = load_athena_config(athena_home)
    selected_traces = args.traces or DEFAULT_TRACES
    selected_routers = args.routers or list(ROUTERS)

    trace_info = {}
    for trace_name in selected_traces:
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
    results: list[MopResult] = []
    experiments = ["Baseline", args.expert_0, args.expert_1, *selected_routers]
    for trace_name in selected_traces:
        for experiment in experiments:
            if experiment == "Baseline":
                flags = build_base_flags(config_module, athena_home, args.warmup_instructions, args.simulation_instructions)
            elif experiment in {args.expert_0, args.expert_1}:
                flags = single_expert_flags(config_module, athena_home, args.warmup_instructions, args.simulation_instructions, experiment)
            else:
                epoch_trace_prefix = None
                if args.epoch_trace:
                    epoch_trace_prefix = output_dir / "epoch_logs" / f"{trace_name}__{experiment}"
                    epoch_trace_prefix.parent.mkdir(parents=True, exist_ok=True)
                flags = mop_flags(
                    config_module,
                    athena_home,
                    args.warmup_instructions,
                    args.simulation_instructions,
                    args.expert_0,
                    args.expert_1,
                    experiment,
                    epoch_trace_prefix,
                )

            print(f"Running {trace_name} + {experiment}", flush=True)
            run_result = run_one(
                binary=binary,
                athena_home=athena_home,
                flags=flags,
                trace_path=local_trace_paths[trace_name],
                trace_name=trace_name,
                experiment=experiment,
                output_dir=output_dir,
            )
            results.append(collect_result(trace_name, experiment, run_result))

    write_summary(results, output_dir, args.expert_0, args.expert_1)
    print(f"Wrote results to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
