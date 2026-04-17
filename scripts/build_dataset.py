#!/usr/bin/env python3
"""Build the analysis-ready tidy dataset for MoP-lite Stage 1.

Reads:
  results/mop_lite/manifest.jsonl      (primary source of truth; one record per run)
  results/mop_lite/metrics/*.json      (all parsed metrics per run, joined via manifest)
  data/splits/official_v1.json         (assigns split side: train / heldout / smoke / other)

Writes:
  data/processed/runs.csv              long-form tidy CSV, one row per run
  data/processed/runs.parquet          (optional, if pyarrow/pandas available)
  data/processed/runs_summary.md       quick summary block for the report appendix

Every row includes split side, experiment kind, seed, git_revision, and per-run
IPC speedups vs Baseline and vs the best single expert for the same trace.

Fail loud: missing manifest -> exit nonzero; missing metrics file referenced
by the manifest -> exit nonzero; IPC missing from a metrics file -> exit nonzero.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def benchmark_family(trace: str) -> str:
    if trace.startswith("parsec_"):
        return "PARSEC"
    if trace.startswith("ligra_"):
        return "LIGRA"
    if trace.startswith("secret_compute_"):
        return "CVP"
    return "SPEC"


def load_split(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text())
    trace_sets = data["trace_sets"]
    side: dict[str, str] = {}
    # Record-most-specific wins: smoke < search_subset < train/heldout.
    for trace in trace_sets.get("full_suite", []):
        side[trace] = "other"
    for trace in trace_sets.get("search_subset", []):
        side[trace] = "search_subset"
    for trace in trace_sets.get("train", []):
        side[trace] = "train"
    for trace in trace_sets.get("heldout", []):
        side[trace] = "heldout"
    # smoke subset membership is informational; don't override train/heldout assignment.
    return side


def load_manifest(path: Path) -> list[dict]:
    assert path.exists(), f"Manifest not found: {path}. Did you run scripts/run_mop_lite.py?"
    rows: list[dict] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    assert rows, f"Manifest is empty: {path}"
    return rows


def load_metrics(metrics_path: Path) -> dict[str, str]:
    assert metrics_path.exists(), f"Metrics file missing: {metrics_path}"
    return json.loads(metrics_path.read_text())


def compute_derived(rows: list[dict]) -> None:
    by_trace: dict[str, list[dict]] = {}
    for row in rows:
        by_trace.setdefault(row["trace"], []).append(row)
    for trace, trace_rows in by_trace.items():
        baseline_candidates = [r for r in trace_rows if r["experiment_kind"] == "baseline"]
        assert baseline_candidates, f"No Baseline run found for trace {trace}"
        # Deduplicate if a trace was run more than once (later run wins).
        baseline = baseline_candidates[-1]
        baseline_ipc = float(baseline["ipc"])
        single_rows = [r for r in trace_rows if r["experiment_kind"] == "single"]
        best_single_ipc = max((float(r["ipc"]) for r in single_rows), default=baseline_ipc)
        for row in trace_rows:
            ipc = float(row["ipc"])
            row["speedup_vs_baseline"] = ipc / baseline_ipc if baseline_ipc else float("nan")
            row["speedup_vs_best_single"] = ipc / best_single_ipc if best_single_ipc else float("nan")
            row["baseline_ipc"] = baseline_ipc
            row["best_single_ipc"] = best_single_ipc
            baseline_traffic = float(baseline["l2c_prefetch_issued"])
            row["traffic_overhead_vs_baseline"] = (
                (float(row["l2c_prefetch_issued"]) - baseline_traffic) / baseline_traffic
                if baseline_traffic else float(row["l2c_prefetch_issued"] > 0)
            )


def pick_metric(metrics: dict[str, str], key: str, required: bool = False) -> float | None:
    if key not in metrics:
        if required:
            raise AssertionError(f"Required metric {key} missing from metrics dict")
        return None
    try:
        return float(metrics[key])
    except ValueError:
        return None


def build_rows(manifest_rows: list[dict], split_side: dict[str, str], root: Path) -> list[dict]:
    out: list[dict] = []
    for record in manifest_rows:
        metrics_path = Path(record["metrics_path"])
        if not metrics_path.is_absolute():
            metrics_path = root / metrics_path
        metrics = load_metrics(metrics_path)
        # Sanity-check IPC.
        ipc = pick_metric(metrics, "Core_0_cumulative_IPC", required=True)
        assert abs(ipc - float(record["ipc"])) < 1e-4, (
            f"IPC mismatch between manifest and metrics for {record['trace']}/{record['experiment']}"
        )
        assert record["trace"] in split_side, (
            f"Trace {record['trace']} is missing from the frozen split artifact; refusing to admit off-protocol data"
        )
        row = dict(record)  # copy
        row["split_side"] = split_side[record["trace"]]
        row["benchmark_family"] = benchmark_family(record["trace"])
        # Pull a few useful derived metrics directly from the metrics file.
        row["l1d_load_miss"] = pick_metric(metrics, "Core_0_L1D_load_miss")
        row["llc_prefetch_useful"] = pick_metric(metrics, "Core_0_LLC_prefetch_useful")
        row["l2c_total_miss"] = pick_metric(metrics, "Core_0_L2C_total_miss")
        row["l2c_rq_full"] = pick_metric(metrics, "Core_0_L2C_rq_full")
        row["l2c_wq_full"] = pick_metric(metrics, "Core_0_L2C_wq_full")
        row["l2c_pq_full"] = pick_metric(metrics, "Core_0_L2C_pq_full")
        row["dram_rq_row_buffer_miss"] = pick_metric(metrics, "Channel_0_RQ_row_buffer_miss")
        row["dram_bus_congested"] = pick_metric(metrics, "Channel_0_dbus_congested")
        row["dram_mshr_full"] = pick_metric(metrics, "Core_0_DDRP_dram_MSHR_full")
        row["branch_pred_mpki"] = pick_metric(metrics, "Core_0_branch_pred_mpki")
        row["cycles"] = pick_metric(metrics, "Core_0_cycles")
        row["total_instructions"] = pick_metric(metrics, "Core_0_total_instructions")
        # Expert utilisation ratios (0 if router didn't issue, nan if no signal).
        for i in (0, 1):
            issued = float(record[f"pref{i}_issued_total"])
            useful = float(record[f"pref{i}_useful_total"])
            row[f"pref{i}_accuracy"] = useful / issued if issued else 0.0
        out.append(row)
    return out


def write_csv(rows: list[dict], path: Path) -> None:
    assert rows, "Nothing to write"
    # Stable column order: identity first, metrics next, config last.
    priority = [
        "trace", "benchmark_family", "split_side", "experiment", "experiment_kind", "router",
        "builtin_coordinator", "expert_0", "expert_1", "seed",
        "ipc", "speedup_vs_baseline", "speedup_vs_best_single",
        "baseline_ipc", "best_single_ipc", "traffic_overhead_vs_baseline",
        "l2c_load_miss", "l2c_mpki",
        "l2c_prefetch_issued_raw", "l2c_prefetch_issued", "l2c_prefetch_useful",
        "l2c_prefetch_useless", "l2c_prefetch_late",
        "downstream_prefetch_accuracy",
        "pref0_issued_total", "pref1_issued_total",
        "pref0_useful_total", "pref1_useful_total",
        "pref0_budget_total", "pref1_budget_total",
        "pref0_selected_epochs", "pref1_selected_epochs",
        "pref0_accuracy", "pref1_accuracy",
        "l1d_load_miss", "llc_prefetch_useful", "l2c_total_miss",
        "l2c_rq_full", "l2c_wq_full", "l2c_pq_full",
        "dram_rq_row_buffer_miss", "dram_bus_congested", "dram_mshr_full",
        "branch_pred_mpki", "cycles", "total_instructions",
        "warmup_instructions", "simulation_instructions",
        "epoch_len_instructions", "mop_total_budget", "mop_accuracy_floor",
        "mop_fixed_split_ratio", "mop_score_weights",
        "mode", "host", "git_revision", "duration_s",
        "start_utc", "end_utc",
        "trace_path", "log_path", "stderr_path", "metrics_path",
        "epoch_trace_prefix", "flags",
    ]
    fieldnames = priority + sorted({k for row in rows for k in row.keys()} - set(priority))
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_summary_md(rows: list[dict], path: Path) -> None:
    total = len(rows)
    by_kind: dict[str, int] = {}
    by_split: dict[str, int] = {}
    traces = set()
    for row in rows:
        by_kind[row["experiment_kind"]] = by_kind.get(row["experiment_kind"], 0) + 1
        by_split[row["split_side"]] = by_split.get(row["split_side"], 0) + 1
        traces.add(row["trace"])
    lines = [
        "# runs.csv summary",
        "",
        f"Total runs: {total}",
        f"Distinct traces: {len(traces)}",
        "",
        "## By experiment kind",
        "",
        *(f"- {k}: {v}" for k, v in sorted(by_kind.items())),
        "",
        "## By split side",
        "",
        *(f"- {k}: {v}" for k, v in sorted(by_split.items())),
        "",
    ]
    path.write_text("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path,
                        default=repo_root() / "results" / "mop_lite" / "manifest.jsonl")
    parser.add_argument("--split",    type=Path,
                        default=repo_root() / "data" / "splits" / "official_v1.json")
    parser.add_argument("--out-csv",  type=Path,
                        default=repo_root() / "data" / "processed" / "runs.csv")
    parser.add_argument("--out-summary", type=Path,
                        default=repo_root() / "data" / "processed" / "runs_summary.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()
    manifest_rows = load_manifest(args.manifest)
    split_side = load_split(args.split)
    rows = build_rows(manifest_rows, split_side, root)
    compute_derived(rows)
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    write_csv(rows, args.out_csv)
    write_summary_md(rows, args.out_summary)
    print(f"Wrote {len(rows)} rows to {args.out_csv}")
    print(f"Summary: {args.out_summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
