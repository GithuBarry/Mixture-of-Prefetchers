#!/usr/bin/env python3
"""Generate report figures and tables from data/processed/runs.csv.

Produces under report/figures/ and report/tables/:

  figures/
    ipc_speedup_vs_nopref.png            per-trace speedup vs Baseline
    ipc_speedup_vs_best_single.png       per-trace speedup vs best single expert
    win_loss_mop_vs_best_single.png      MoP-lite delta vs best single (bar, sorted)
    accuracy_vs_traffic.png              downstream accuracy vs L2 prefetch issued (scatter)

  tables/
    router_ablation.md                   per-router geomean speedups (train + heldout)
    expert_pair_ablation.md              pair-level table (currently 1 pair, extensible)
    hardware_budget.md                   MoP-lite storage/compute footprint

All figures are generated via matplotlib's default style; no seaborn. If a figure
would be trivially empty (e.g. no MoP-lite rows), that figure is skipped and a
warning is printed instead of producing a misleading blank chart.
"""
from __future__ import annotations

import argparse
import csv
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_rows(csv_path: Path) -> list[dict]:
    assert csv_path.exists(), f"Dataset not found: {csv_path}. Run scripts/build_dataset.py first."
    with csv_path.open() as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    assert rows, f"Dataset is empty: {csv_path}"
    # Coerce numeric fields we care about.
    numeric = [
        "ipc", "speedup_vs_baseline", "speedup_vs_best_single",
        "l2c_prefetch_issued", "l2c_prefetch_useful",
        "downstream_prefetch_accuracy", "l2c_mpki",
        "pref0_accuracy", "pref1_accuracy",
        "pref0_budget_total", "pref1_budget_total",
        "pref0_issued_total", "pref1_issued_total",
    ]
    for row in rows:
        for key in numeric:
            if row.get(key) in (None, ""):
                row[key] = math.nan
            else:
                try:
                    row[key] = float(row[key])
                except ValueError:
                    row[key] = math.nan
    return rows


def geomean(values: list[float]) -> float:
    cleaned = [v for v in values if v and not math.isnan(v) and v > 0]
    if not cleaned:
        return float("nan")
    return math.exp(statistics.fmean(math.log(v) for v in cleaned))


def skip_output(out_path: Path, reason: str) -> None:
    out_path.unlink(missing_ok=True)
    print(f"[skip] {out_path.name}: {reason}")


# -- Figure 1: IPC speedup vs no-pref (Baseline) ---------------------------------

def fig_speedup_vs_nopref(rows: list[dict], out_path: Path) -> None:
    plot_rows = [r for r in rows if r["experiment_kind"] != "baseline"]
    if not plot_rows:
        skip_output(out_path, "no non-baseline runs")
        return
    traces = sorted({r["trace"] for r in plot_rows})
    experiments = sorted({r["experiment"] for r in plot_rows})
    fig, ax = plt.subplots(figsize=(max(6, len(traces) * 0.9), 4))
    width = 0.8 / max(1, len(experiments))
    for i, experiment in enumerate(experiments):
        xs = []
        ys = []
        for j, trace in enumerate(traces):
            match = [r for r in plot_rows if r["trace"] == trace and r["experiment"] == experiment]
            if not match:
                continue
            xs.append(j + (i - len(experiments) / 2) * width + width / 2)
            ys.append(match[-1]["speedup_vs_baseline"])
        ax.bar(xs, ys, width=width, label=experiment)
    ax.axhline(1.0, color="k", linestyle=":", linewidth=0.8)
    ax.set_xticks(range(len(traces)))
    ax.set_xticklabels([t[:22] for t in traces], rotation=45, ha="right")
    ax.set_ylabel("IPC speedup vs no-prefetch")
    ax.set_title("IPC speedup vs no-prefetch baseline")
    ax.legend(fontsize=7, ncols=2)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


# -- Figure 2: IPC speedup vs best single expert ---------------------------------

def fig_speedup_vs_best_single(rows: list[dict], out_path: Path) -> None:
    coord_rows = [r for r in rows if r["experiment_kind"] in {"router", "builtin"}]
    if not coord_rows:
        skip_output(out_path, "no coordinator runs")
        return
    traces = sorted({r["trace"] for r in coord_rows})
    experiments = sorted({r["experiment"] for r in coord_rows})
    fig, ax = plt.subplots(figsize=(max(6, len(traces) * 0.9), 4))
    width = 0.8 / max(1, len(experiments))
    for i, experiment in enumerate(experiments):
        xs, ys = [], []
        for j, trace in enumerate(traces):
            match = [r for r in coord_rows if r["trace"] == trace and r["experiment"] == experiment]
            if not match:
                continue
            xs.append(j + (i - len(experiments) / 2) * width + width / 2)
            ys.append(match[-1]["speedup_vs_best_single"])
        ax.bar(xs, ys, width=width, label=experiment)
    ax.axhline(1.0, color="k", linestyle=":", linewidth=0.8)
    ax.set_xticks(range(len(traces)))
    ax.set_xticklabels([t[:22] for t in traces], rotation=45, ha="right")
    ax.set_ylabel("IPC speedup vs best single expert")
    ax.set_title("Coordinator speedup over best single expert per trace")
    ax.legend(fontsize=7, ncols=2)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


# -- Figure 3: MoP-lite vs best single (sorted bar) ------------------------------

def fig_win_loss(rows: list[dict], out_path: Path) -> None:
    mop = [r for r in rows if r["experiment"] == "MoPLite"]
    if not mop:
        skip_output(out_path, "no MoPLite runs")
        return
    mop.sort(key=lambda r: r["speedup_vs_best_single"])
    labels = [r["trace"][:28] for r in mop]
    deltas = [(r["speedup_vs_best_single"] - 1.0) * 100.0 for r in mop]
    colors = ["#2a9d8f" if d >= 0 else "#e76f51" for d in deltas]
    fig, ax = plt.subplots(figsize=(7, max(3, 0.3 * len(labels))))
    ax.barh(labels, deltas, color=colors)
    ax.axvline(0.0, color="k", linewidth=0.6)
    ax.set_xlabel("Δ IPC vs best single expert (%)")
    ax.set_title("MoP-lite per-trace win/loss vs best single expert")
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


# -- Figure 4: accuracy vs traffic scatter ---------------------------------------

def fig_accuracy_vs_traffic(rows: list[dict], out_path: Path) -> None:
    plot_rows = [r for r in rows if r["experiment_kind"] != "baseline" and r["l2c_prefetch_issued"] > 0]
    if not plot_rows:
        skip_output(out_path, "no prefetcher runs with issued traffic")
        return
    fig, ax = plt.subplots(figsize=(6, 4))
    experiments = sorted({r["experiment"] for r in plot_rows})
    for experiment in experiments:
        subset = [r for r in plot_rows if r["experiment"] == experiment]
        xs = [r["l2c_prefetch_issued"] for r in subset]
        ys = [r["downstream_prefetch_accuracy"] * 100.0 for r in subset]
        ax.scatter(xs, ys, label=experiment, alpha=0.8, s=32)
    ax.set_xscale("log")
    ax.set_xlabel("L2 prefetches issued (log, per run)")
    ax.set_ylabel("Downstream prefetch accuracy (%)")
    ax.set_title("Accuracy vs traffic per run")
    ax.legend(fontsize=7, ncols=2)
    ax.grid(True, which="both", linestyle=":", linewidth=0.4)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


# -- Table: router ablation ------------------------------------------------------

def table_router_ablation(rows: list[dict], out_path: Path) -> None:
    by_experiment: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in rows:
        if r["experiment_kind"] not in {"router", "builtin"}:
            continue
        split = r["split_side"]
        by_experiment[(r["experiment"], split)].append(r["speedup_vs_best_single"])

    lines = [
        "# Router / coordinator ablation",
        "",
        "Geometric mean of IPC speedup vs best single expert, by split side.",
        "Reported only for (experiment, split) cells that contain runs.",
        "",
        "| Coordinator | Split | Runs | Geomean vs best single | Min | Max |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    if not by_experiment:
        lines.append("| _(no coordinator runs yet)_ | - | 0 | - | - | - |")
    for (experiment, split), values in sorted(by_experiment.items()):
        gmean = geomean(values)
        lo = min(values) if values else float("nan")
        hi = max(values) if values else float("nan")
        lines.append(
            f"| {experiment} | {split} | {len(values)} | "
            f"{gmean:.4f} | {lo:.4f} | {hi:.4f} |"
        )
    out_path.write_text("\n".join(lines) + "\n")


# -- Table: expert pair ablation -------------------------------------------------

def table_expert_pair(rows: list[dict], out_path: Path) -> None:
    # Currently only one pair is in scope (Pythia + SPP+PPF). We emit a placeholder
    # row per pair observed, ready to extend when additional pairs are added.
    pairs: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in rows:
        if r["experiment"] != "MoPLite":
            continue
        key = (r.get("expert_0") or "?", r.get("expert_1") or "?")
        pairs[key].append(r["speedup_vs_best_single"])
    lines = [
        "# Expert-pair ablation (MoP-lite router only)",
        "",
        "| Expert 0 | Expert 1 | Runs | Geomean speedup vs best single |",
        "| --- | --- | ---: | ---: |",
    ]
    if not pairs:
        lines.append("| - | - | 0 | - |")
    for (e0, e1), values in sorted(pairs.items()):
        lines.append(f"| {e0} | {e1} | {len(values)} | {geomean(values):.4f} |")
    out_path.write_text("\n".join(lines) + "\n")


# -- Table: hardware budget ------------------------------------------------------

HARDWARE_BUDGET_STATIC = """# MoP-lite hardware / storage budget (Stage 1)

Scope-locked Stage 1 control surface (see charter § MoP-lite control surface):

| Component                    | Configuration                              | Approx. storage |
| ---                          | ---                                        | ---             |
| Per-epoch counters (2 experts)| `pref_issued[2]`, `pref_useful[2]` (uint64)| 32 B            |
| Usefulness/coverage cache    | `pref_acc[2]`, coverage deltas (float)     | 16 B            |
| Budget registers             | `mop_total_budget`, share per expert       | 8 B             |
| Router state                 | `action` (3 values), epoch counter         | 4 B             |
| One-shot fit scratchpad      | `score_sum[2]`, `score_count`              | 24 B            |
| Score weights (frozen)       | 3 floats                                   | 12 B            |
| Accuracy floor / fixed ratio | 2 uint8                                    | 2 B             |
| **Total (rounded)**          |                                            | **≈ 100 B**     |

The epoch length is 500 000 retired instructions (`og_instr_epoch_len`), so
update frequency ≈ 2 kHz at 1 GHz effective IPC — entirely negligible
arithmetic cost. No per-access ML inference is introduced in Stage 1.
"""


def table_hardware_budget(out_path: Path) -> None:
    out_path.write_text(HARDWARE_BUDGET_STATIC)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", type=Path, default=repo_root() / "data" / "processed" / "runs.csv")
    p.add_argument("--figures-dir", type=Path, default=repo_root() / "report" / "figures")
    p.add_argument("--tables-dir",  type=Path, default=repo_root() / "report" / "tables")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    args.figures_dir.mkdir(parents=True, exist_ok=True)
    args.tables_dir.mkdir(parents=True, exist_ok=True)
    rows = load_rows(args.csv)
    fig_speedup_vs_nopref     (rows, args.figures_dir / "ipc_speedup_vs_nopref.png")
    fig_speedup_vs_best_single(rows, args.figures_dir / "ipc_speedup_vs_best_single.png")
    fig_win_loss              (rows, args.figures_dir / "win_loss_mop_vs_best_single.png")
    fig_accuracy_vs_traffic   (rows, args.figures_dir / "accuracy_vs_traffic.png")
    table_router_ablation     (rows, args.tables_dir / "router_ablation.md")
    table_expert_pair         (rows, args.tables_dir / "expert_pair_ablation.md")
    table_hardware_budget     (args.tables_dir / "hardware_budget.md")
    print(f"Figures: {args.figures_dir}")
    print(f"Tables:  {args.tables_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
