#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import re
import shlex
import subprocess
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path


DEFAULT_TRACES = [
    "parsec_2.1.fluidanimate.simlarge.prebuilt.drop_9500M.length_250M",
    "parsec_2.1.streamcluster.simlarge.prebuilt.drop_0M.length_250M",
]

EXPERIMENTS = {
    "Baseline": [],
    "Pythia": ["PYTHIA"],
    "SPP+PPF": ["SPP+PPF"],
    "MLOP": ["MLOP"],
    "SMS": ["SMS"],
}

ZENODO_RECORD = "17850673"
DEFAULT_WORKERS = 8
SAFE_TRACE_ROOT = Path("/tmp/mop_athena_traces")


@dataclass(frozen=True)
class RunResult:
    trace: str
    experiment: str
    ipc: float
    l2c_prefetch_issued: float
    downstream_prefetch_useful: float
    downstream_prefetch_accuracy: float
    log_path: Path
    err_path: Path
    metrics_path: Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_athena_config(athena_home: Path):
    os_environ = dict(ATHENA_HOME=str(athena_home))
    original = dict(**os_environ)
    spec = importlib.util.spec_from_file_location(
        "athena_project_config", athena_home / "scripts" / "config.py"
    )
    assert spec and spec.loader, "Failed to load Athena config.py"
    module = importlib.util.module_from_spec(spec)
    old_athena_home = None
    if "ATHENA_HOME" in __import__("os").environ:
        old_athena_home = __import__("os").environ["ATHENA_HOME"]
    __import__("os").environ.update(original)
    try:
        spec.loader.exec_module(module)
    finally:
        if old_athena_home is None:
            __import__("os").environ.pop("ATHENA_HOME", None)
        else:
            __import__("os").environ["ATHENA_HOME"] = old_athena_home
    return module


def replace_flag_value(flag_string: str, flag_name: str, value: int) -> str:
    pattern = rf"{re.escape(flag_name)}=\d+"
    replaced = re.sub(pattern, f"{flag_name}={value}", flag_string)
    assert replaced != flag_string, f"Could not find {flag_name} in Athena BASE flags"
    return replaced


def build_experiment_flags(config_module, athena_home: Path, experiment: str, warmup: int, sim: int) -> str:
    assert experiment in EXPERIMENTS, f"Unsupported experiment: {experiment}"
    flags = config_module.EXP_VARIABLES["BASE"]
    flags = replace_flag_value(flags, "--warmup_instructions", warmup)
    flags = replace_flag_value(flags, "--simulation_instructions", sim)
    for key in EXPERIMENTS[experiment]:
        flags = f"{flags} {config_module.EXP_VARIABLES[key]}"
    return flags.replace("$(ATHENA_HOME)", shlex.quote(str(athena_home)))


def normalize_trace_path(raw_path: str) -> str:
    suffix = raw_path.split("/traces/", 1)[1]
    return suffix


def zenodo_trace_url(trace_filename: str) -> str:
    encoded = urllib.parse.quote(trace_filename, safe="")
    return f"https://zenodo.org/api/records/{ZENODO_RECORD}/files/{encoded}/content"


def download_trace(trace_name: str, trace_info: dict, traces_dir: Path) -> Path:
    traces_dir.mkdir(parents=True, exist_ok=True)
    filename = normalize_trace_path(trace_info["path"])
    target = traces_dir / filename
    if target.exists():
        return target
    url = zenodo_trace_url(filename)
    print(f"Downloading {trace_name} -> {target.name}", flush=True)
    with urllib.request.urlopen(url) as response, target.open("wb") as out:
        while True:
            chunk = response.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
    return target


def build_athena_if_needed(athena_home: Path) -> Path:
    binary = athena_home / "bin" / "champsim"
    if binary.exists():
        return binary
    subprocess.run(["make", "-C", str(athena_home), "-j4"], check=True)
    assert binary.exists(), "Athena build finished without bin/champsim"
    return binary


def parse_metrics(stdout: str) -> dict[str, str]:
    metrics: dict[str, str] = {}
    for line in stdout.splitlines():
        line = line.strip()
        if line.count(" ") != 1:
            continue
        key, value = line.split(" ", 1)
        metrics[key.strip()] = value.strip()
    return metrics


def metric_float(metrics: dict[str, str], key: str, default: float | None = None) -> float:
    if key not in metrics:
        if default is not None:
            return default
        raise AssertionError(f"Missing metric: {key}")
    return float(metrics[key])


def run_one(
    binary: Path,
    athena_home: Path,
    flags: str,
    trace_path: Path,
    trace_name: str,
    experiment: str,
    output_dir: Path,
) -> RunResult:
    safe_trace = trace_name.replace("/", "_")
    safe_experiment = experiment.replace("+", "plus").replace(" ", "_")
    log_path = output_dir / "logs" / f"{safe_trace}__{safe_experiment}.out"
    err_path = output_dir / "logs" / f"{safe_trace}__{safe_experiment}.err"
    metrics_path = output_dir / "metrics" / f"{safe_trace}__{safe_experiment}.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)

    trace_arg = shell_safe_trace_path(trace_path)
    cmd = [str(binary), *shlex.split(flags), "-traces", str(trace_arg)]
    env = dict(__import__("os").environ)
    env["ATHENA_HOME"] = str(athena_home)
    completed = subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)
    log_path.write_text(completed.stdout)
    err_path.write_text(completed.stderr)
    if completed.returncode != 0:
        raise subprocess.CalledProcessError(
            completed.returncode,
            cmd,
            output=completed.stdout,
            stderr=completed.stderr,
        )
    metrics = parse_metrics(completed.stdout)
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True))
    assert "Core_0_cumulative_IPC" in metrics, f"IPC missing from {log_path}"
    l2c_prefetch_issued = metric_float(metrics, "Core_0_L2C_prefetch_issued")
    downstream_prefetch_useful = (
        metric_float(metrics, "Core_0_L2C_prefetch_useful")
        + metric_float(metrics, "Core_0_LLC_prefetch_useful")
    )
    downstream_prefetch_accuracy = 0.0
    if l2c_prefetch_issued:
        downstream_prefetch_accuracy = downstream_prefetch_useful / l2c_prefetch_issued
    return RunResult(
        trace=trace_name,
        experiment=experiment,
        ipc=float(metrics["Core_0_cumulative_IPC"]),
        l2c_prefetch_issued=l2c_prefetch_issued,
        downstream_prefetch_useful=downstream_prefetch_useful,
        downstream_prefetch_accuracy=downstream_prefetch_accuracy,
        log_path=log_path,
        err_path=err_path,
        metrics_path=metrics_path,
    )


def shell_safe_trace_path(trace_path: Path) -> Path:
    trace_path = trace_path.resolve()
    if trace_path.parent == SAFE_TRACE_ROOT:
        return trace_path
    SAFE_TRACE_ROOT.mkdir(parents=True, exist_ok=True)
    safe_path = SAFE_TRACE_ROOT / trace_path.name
    if safe_path.is_symlink() or safe_path.exists():
        assert safe_path.resolve() == trace_path, (
            f"Safe trace path collision: {safe_path} already points to {safe_path.resolve()}"
        )
        return safe_path
    try:
        safe_path.symlink_to(trace_path)
    except FileExistsError:
        assert safe_path.resolve() == trace_path, (
            f"Safe trace path collision: {safe_path} already points to {safe_path.resolve()}"
        )
    return safe_path


def write_summary(results: list[RunResult], output_dir: Path) -> None:
    summary_csv = output_dir / "summary.csv"
    summary_md = output_dir / "summary.md"
    by_trace: dict[str, list[RunResult]] = {}
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
                "l2c_prefetch_issued",
                "downstream_prefetch_useful",
                "downstream_prefetch_accuracy",
                "log",
                "metrics",
            ]
        )
        for trace in sorted(by_trace):
            trace_results = sorted(by_trace[trace], key=lambda item: item.experiment)
            baseline = next(item for item in trace_results if item.experiment == "Baseline")
            for item in trace_results:
                writer.writerow(
                    [
                        item.trace,
                        item.experiment,
                        f"{item.ipc:.6f}",
                        f"{item.ipc / baseline.ipc:.6f}",
                        f"{item.l2c_prefetch_issued:.0f}",
                        f"{item.downstream_prefetch_useful:.0f}",
                        f"{item.downstream_prefetch_accuracy:.6f}",
                        item.log_path,
                        item.metrics_path,
                    ]
                )

    lines = [
        "# Single-Prefetcher Baseline Validation",
        "",
        "| Trace | Baseline IPC | Best single-prefetcher | IPC | Speedup vs Baseline | Downstream accuracy |",
        "| --- | ---: | --- | ---: | ---: | ---: |",
    ]
    for trace in sorted(by_trace):
        trace_results = sorted(by_trace[trace], key=lambda item: item.ipc, reverse=True)
        baseline = next(item for item in trace_results if item.experiment == "Baseline")
        best = trace_results[0]
        lines.append(
            f"| {trace} | {baseline.ipc:.4f} | {best.experiment} | {best.ipc:.4f} | {best.ipc / baseline.ipc:.4f}x | {best.downstream_prefetch_accuracy:.2%} |"
        )
    summary_md.write_text("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--trace",
        dest="traces",
        action="append",
        help="Athena trace name from external/athena/scripts/config.py. Repeat to run more than one.",
    )
    parser.add_argument(
        "--experiment",
        dest="experiments",
        action="append",
        choices=sorted(EXPERIMENTS),
        help="Subset of experiments to run. Repeat to run more than one.",
    )
    parser.add_argument("--warmup-instructions", type=int, default=20_000_000)
    parser.add_argument("--simulation-instructions", type=int, default=50_000_000)
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help="Maximum concurrent simulator processes (default: 8). Use 1 for serial execution.",
    )
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--download-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    assert args.workers > 0, "--workers must be >= 1"
    root = repo_root()
    athena_home = root / "external" / "athena"
    traces_dir = root / "artifacts" / "athena_traces"
    output_dir = root / "results" / "single_prefetcher_baselines"
    output_dir.mkdir(parents=True, exist_ok=True)

    config_module = load_athena_config(athena_home)
    selected_traces = args.traces or DEFAULT_TRACES
    selected_experiments = args.experiments or list(EXPERIMENTS)

    trace_info = {}
    for trace_name in selected_traces:
        assert trace_name in config_module.TRACE_DATA, f"Unknown Athena trace: {trace_name}"
        trace_info[trace_name] = config_module.get_trace_info(trace_name)

    local_trace_paths = {}
    for trace_name, info in trace_info.items():
        filename = normalize_trace_path(info["path"])
        local_path = traces_dir / filename
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
    planned_runs: list[tuple[str, str, str]] = []
    for trace_name in selected_traces:
        for experiment in selected_experiments:
            flags = build_experiment_flags(
                config_module,
                athena_home,
                experiment,
                args.warmup_instructions,
                args.simulation_instructions,
            )
            planned_runs.append((trace_name, experiment, flags))

    results: list[RunResult] = []
    print(
        f"Launching {len(planned_runs)} runs with up to {args.workers} workers",
        flush=True,
    )
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_job = {}
        for trace_name, experiment, flags in planned_runs:
            print(f"Queueing {trace_name} + {experiment}", flush=True)
            future = executor.submit(
                run_one,
                binary=binary,
                athena_home=athena_home,
                flags=flags,
                trace_path=safe_trace_paths[trace_name],
                trace_name=trace_name,
                experiment=experiment,
                output_dir=output_dir,
            )
            future_to_job[future] = (trace_name, experiment)

        for future in as_completed(future_to_job):
            trace_name, experiment = future_to_job[future]
            results.append(future.result())
            print(f"Finished {trace_name} + {experiment}", flush=True)

    write_summary(results, output_dir)
    print(f"Wrote results to {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
