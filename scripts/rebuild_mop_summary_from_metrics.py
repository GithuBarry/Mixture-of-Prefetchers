#!/usr/bin/env python3
"""Rebuild a MoP summary.csv from complete raw metric JSON artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from run_mop_lite import collect_result, write_summary
from run_single_prefetcher_baselines import RunResult, metric_float


SAFE_EXPERIMENTS = {
    "Baseline": "Baseline",
    "MLOP": "MLOP",
    "SPPplusPPF": "SPP+PPF",
    "MoP-V1.2": "MoP-V1.2",
    "MoP-V1.3": "MoP-V1.3",
}


def experiment_kind(experiment: str, expert0: str, expert1: str) -> str:
    if experiment == "Baseline":
        return "baseline"
    if experiment in {expert0, expert1}:
        return "single"
    if experiment.startswith("MoP-"):
        return "router"
    return "builtin"


def parse_metric_path(path: Path) -> tuple[str, str]:
    trace, safe_experiment = path.stem.rsplit("__", 1)
    assert safe_experiment in SAFE_EXPERIMENTS, f"Unknown experiment in {path}"
    return trace, SAFE_EXPERIMENTS[safe_experiment]


def run_result_from_metric(path: Path) -> RunResult:
    trace, experiment = parse_metric_path(path)
    metrics = json.loads(path.read_text())
    log_path = path.parents[1] / "logs" / f"{path.stem}.out"
    err_path = path.parents[1] / "logs" / f"{path.stem}.err"
    return RunResult(
        trace=trace,
        experiment=experiment,
        ipc=metric_float(metrics, "Core_0_cumulative_IPC"),
        l2c_prefetch_issued=metric_float(metrics, "Core_0_L2C_prefetch_issued"),
        downstream_prefetch_useful=(
            metric_float(metrics, "Core_0_L2C_prefetch_useful")
            + metric_float(metrics, "Core_0_LLC_prefetch_useful")
        ),
        downstream_prefetch_accuracy=0.0,
        log_path=log_path,
        err_path=err_path,
        metrics_path=path,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--expert-0", default="MLOP")
    parser.add_argument("--expert-1", default="SPP+PPF")
    parser.add_argument("--expected-runs", type=int, default=28)
    args = parser.parse_args()

    metric_paths = sorted(args.results_dir.glob("runs/*/metrics/*.json"))
    assert len(metric_paths) == args.expected_runs, (
        f"Expected {args.expected_runs} metric files, found {len(metric_paths)}"
    )
    results = []
    for metric_path in metric_paths:
        run_result = run_result_from_metric(metric_path)
        kind = experiment_kind(run_result.experiment, args.expert_0, args.expert_1)
        results.append(collect_result(run_result.trace, run_result.experiment, kind, run_result))
    traces = {result.trace for result in results}
    assert all(
        len([result for result in results if result.trace == trace]) == 4
        for trace in traces
    ), "Each trace must have baseline, two singles, and one router"
    write_summary(results, args.results_dir, args.expert_0, args.expert_1)
    provenance = {
        "source": "rebuild_mop_summary_from_metrics.py",
        "metric_files": len(metric_paths),
        "traces": sorted(traces),
        "note": "summary.csv and summary.md rebuilt from complete raw metric JSON files.",
    }
    (args.results_dir / "summary_rebuild_provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(provenance, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
