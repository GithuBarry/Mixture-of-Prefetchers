#!/usr/bin/env python3
"""Generate report figures and tables from data/processed/runs.csv.

Produces under report/figures/ and report/tables/:

  figures/
    ipc_speedup_summary.png              combined speedup summary figure
    win_loss_mop_vs_best_single.png      MoP-lite delta vs best single (bar, sorted)
    single_expert_profiles.png          per-trace winning single-expert profile
    mop_vs_reference_rows.png           per-trace MoPLite vs reference rows

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


PALETTE = {
    "amber": "#ffb000",
    "orange": "#fe6100",
    "magenta": "#dc267f",
    "purple": "#785ef0",
    "blue": "#648fff",
    "black": "#000000",
    "light_grey": "#d9d9d9",
    "mid_grey": "#8f8f8f",
    "white": "#ffffff",
}

EXPERIMENT_COLORS = {
    "AthenaMAB": PALETTE["amber"],
    "OneShotFit": PALETTE["orange"],
    "MoPLite": PALETTE["magenta"],
    "WinnerTakeAll": PALETTE["purple"],
    "FixedSplit": PALETTE["blue"],
    "RandomRouter": PALETTE["light_grey"],
    "SPP+PPF": PALETTE["purple"],
    "Pythia": PALETTE["blue"],
    "MLOP": PALETTE["mid_grey"],
    "SMS": PALETTE["light_grey"],
}

SPLIT_ORDER = {"train": 0, "search_subset": 0, "heldout": 1, "other": 2, "unknown": 3}
SPLIT_LABEL = {"train": "Search-side subset", "heldout": "Held-out"}

plt.rcParams.update(
    {
        "figure.facecolor": PALETTE["white"],
        "axes.facecolor": PALETTE["white"],
        "axes.edgecolor": PALETTE["black"],
        "axes.labelcolor": PALETTE["black"],
        "xtick.color": PALETTE["black"],
        "ytick.color": PALETTE["black"],
        "grid.color": PALETTE["light_grey"],
        "grid.linewidth": 0.6,
    }
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def experiment_color(name: str) -> str:
    return EXPERIMENT_COLORS.get(name, PALETTE["black"])


def ordered_traces(rows: list[dict]) -> list[str]:
    split_for_trace = {r["trace"]: r.get("split_side", "unknown") for r in rows}
    return sorted(split_for_trace, key=lambda t: (SPLIT_ORDER.get(split_for_trace[t], 99), t))


def draw_split_separator(ax, traces: list[str], rows: list[dict]) -> None:
    split_for_trace = {r["trace"]: r.get("split_side", "unknown") for r in rows}
    for idx in range(1, len(traces)):
        if split_for_trace[traces[idx - 1]] != split_for_trace[traces[idx]]:
            ax.axvline(idx - 0.5, color=PALETTE["light_grey"], linewidth=1.0)


def split_summary(rows: list[dict], experiments: list[str], metric: str) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for split in ["train", "heldout"]:
        split_rows = [r for r in rows if r.get("split_side") == split]
        if not split_rows:
            continue
        out[split] = {}
        for experiment in experiments:
            vals = [r[metric] for r in split_rows if r["experiment"] == experiment and not math.isnan(r[metric])]
            if vals:
                out[split][experiment] = geomean(vals)
    return out


def experiment_order(experiments: list[str]) -> list[str]:
    preferred = [
        "Pythia",
        "SPP+PPF",
        "MLOP",
        "SMS",
        "AthenaMAB",
        "FixedSplit",
        "WinnerTakeAll",
        "RandomRouter",
        "OneShotFit",
        "MoPLite",
    ]
    rank = {name: i for i, name in enumerate(preferred)}
    return sorted(experiments, key=lambda name: (rank.get(name, 999), name))


def draw_split_bars(ax, summaries: dict[str, dict[str, float]], experiments: list[str], xlabel: str, title: str) -> None:
    width = 0.34
    ys = list(range(len(experiments)))
    for offset, split in [(-width / 2, "train"), (width / 2, "heldout")]:
        for j, experiment in enumerate(experiments):
            if split not in summaries or experiment not in summaries[split]:
                continue
            face = experiment_color(experiment) if split == "train" else PALETTE["white"]
            value = summaries[split][experiment]
            ax.barh(
                j + offset,
                value,
                height=width,
                color=face,
                edgecolor=experiment_color(experiment),
                linewidth=1.2,
                hatch="" if split == "train" else "//",
                label=SPLIT_LABEL.get(split, split) if j == 0 else None,
            )
            ax.text(value + 0.002, j + offset, f"{value:.3f}", va="center", ha="left", fontsize=7, color=PALETTE["black"])
    ax.axvline(1.0, color=PALETTE["black"], linestyle=":", linewidth=1.0)
    ax.set_yticks(ys)
    ax.set_yticklabels(experiments)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    ax.grid(True, axis="x", linestyle=":")


def fig_speedup_summary(rows: list[dict], out_path: Path) -> None:
    plot_rows = [r for r in rows if r["experiment_kind"] != "baseline"]
    if not plot_rows:
        skip_output(out_path, "no non-baseline runs")
        return
    experiments = experiment_order(list({r["experiment"] for r in plot_rows}))
    nopref = split_summary(plot_rows, experiments, "speedup_vs_baseline")
    fig, ax = plt.subplots(figsize=(10, max(5, len(experiments) * 0.45)))
    draw_split_bars(ax, nopref, experiments, "Geomean IPC vs prefetch-off", "How much do methods beat prefetch-off?")
    ax.legend(fontsize=8, ncols=2, title="Split")
    fig.text(0.01, 0.01, "Caption: All bars use the same normalization: IPC relative to prefetch-off. Filled bars are the 17-trace training split; hatched white bars are the 7-trace held-out split. Pair-best-single comparisons are intentionally kept out of this figure and shown elsewhere.", ha="left", va="bottom", fontsize=8, color=PALETTE["black"], wrap=True)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def fig_mop_vs_reference_rows(rows: list[dict], out_path: Path) -> None:
    plot_rows = [r for r in rows if r["experiment_kind"] != "baseline"]
    mop_rows = [r for r in plot_rows if r["experiment"] == "MoPLite"]
    if not mop_rows:
        skip_output(out_path, "no MoPLite rows")
        return
    traces = ordered_traces(plot_rows)
    split_for_trace = {r["trace"]: r.get("split_side", "unknown") for r in plot_rows}
    mop_by_trace = {}
    pairbest_by_trace = {}
    best_by_trace = {}
    for trace in traces:
        trace_rows = [r for r in plot_rows if r["trace"] == trace]
        mop = [r for r in trace_rows if r["experiment"] == "MoPLite"]
        if mop:
            mop_by_trace[trace] = mop[0]["speedup_vs_baseline"]
        singles = [r for r in trace_rows if r["experiment_kind"] == "single" and r["experiment"] in {"Pythia", "SPP+PPF"}]
        if singles:
            pairbest_by_trace[trace] = max(r["speedup_vs_baseline"] for r in singles)
        best_by_trace[trace] = max(r["speedup_vs_baseline"] for r in trace_rows)

    fig, ax = plt.subplots(figsize=(10, max(6, len(traces) * 0.35)))
    y = list(range(len(traces)))
    ax.barh(y, [mop_by_trace.get(t, math.nan) for t in traces], color=PALETTE["magenta"], edgecolor=PALETTE["black"], linewidth=0.4, label="MoPLite")
    ax.scatter([pairbest_by_trace.get(t, math.nan) for t in traces], y, color=PALETTE["purple"], edgecolors=PALETTE["black"], linewidths=0.4, s=36, label="Pair-best single")
    ax.scatter([best_by_trace.get(t, math.nan) for t in traces], y, color=PALETTE["white"], edgecolors=PALETTE["black"], linewidths=1.0, s=42, label="Best method in batch")
    ax.axvline(1.0, color=PALETTE["black"], linestyle=":", linewidth=1.0)
    for idx in range(1, len(traces)):
        if split_for_trace[traces[idx - 1]] != split_for_trace[traces[idx]]:
            ax.axhline(idx - 0.5, color=PALETTE["light_grey"], linewidth=1.0)
    ax.set_yticks(y)
    ax.set_yticklabels([t[:30] for t in traces])
    ax.set_xlabel("IPC vs prefetch-off")
    ax.set_title("MoPLite versus two per-trace reference rows")
    ax.grid(True, axis="x", linestyle=":")
    ax.legend(fontsize=8, ncols=3)
    fig.text(0.01, 0.01, "Caption: Pair-best single means max(Pythia, SPP+PPF) on that trace only. Best method in batch is broader: the best of all methods on that trace, including coordinators such as AthenaMAB. Separating them avoids mixing a local two-expert reference with a full-batch skyline.", ha="left", va="bottom", fontsize=8, color=PALETTE["black"], wrap=True)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


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
        "traffic_overhead_vs_baseline",
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
    experiments = experiment_order(list({r["experiment"] for r in plot_rows}))
    summaries = split_summary(plot_rows, experiments, "speedup_vs_baseline")
    fig, ax = plt.subplots(figsize=(9, max(5, len(experiments) * 0.45)))
    width = 0.34
    ys = list(range(len(experiments)))
    for offset, split in [(-width / 2, "train"), (width / 2, "heldout")]:
        for j, experiment in enumerate(experiments):
            if split not in summaries or experiment not in summaries[split]:
                continue
            face = experiment_color(experiment) if split == "train" else PALETTE["white"]
            value = summaries[split][experiment]
            ax.barh(
                j + offset,
                summaries[split][experiment],
                height=width,
                color=face,
                edgecolor=experiment_color(experiment),
                linewidth=1.2,
                hatch="" if split == "train" else "//",
                label=split if j == 0 else None,
            )
            ax.text(value + 0.002, j + offset, f"{value:.3f}", va="center", ha="left", fontsize=7, color=PALETTE["black"])
    ax.axvline(1.0, color=PALETTE["black"], linestyle=":", linewidth=1.0)
    ax.set_yticks(ys)
    ax.set_yticklabels(experiments)
    ax.set_xlabel("Geomean IPC vs no-prefetch")
    ax.set_title("How much do methods beat no-prefetch?")
    ax.legend(fontsize=8, ncols=2, title="Split")
    ax.grid(True, axis="x", linestyle=":")
    fig.text(0.01, 0.01, "Caption: This summary asks only one question: which methods improve IPC over no-prefetch, and by how much on the search-side subset versus held-out traces?", ha="left", va="bottom", fontsize=8, color=PALETTE["black"], wrap=True)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


# -- Figure 2: IPC speedup vs best single expert ---------------------------------

def fig_speedup_vs_best_single(rows: list[dict], out_path: Path) -> None:
    plot_rows = [r for r in rows if r["experiment_kind"] != "baseline"]
    if not plot_rows:
        skip_output(out_path, "no coordinator runs")
        return
    experiments = experiment_order(list({r["experiment"] for r in plot_rows}))
    summaries = split_summary(plot_rows, experiments, "speedup_vs_best_single")
    fig, ax = plt.subplots(figsize=(9, max(5, len(experiments) * 0.45)))
    width = 0.34
    ys = list(range(len(experiments)))
    for offset, split in [(-width / 2, "train"), (width / 2, "heldout")]:
        for j, experiment in enumerate(experiments):
            if split not in summaries or experiment not in summaries[split]:
                continue
            face = experiment_color(experiment) if split == "train" else PALETTE["white"]
            value = summaries[split][experiment]
            ax.barh(
                j + offset,
                summaries[split][experiment],
                height=width,
                color=face,
                edgecolor=experiment_color(experiment),
                linewidth=1.2,
                hatch="" if split == "train" else "//",
                label=split if j == 0 else None,
            )
            ax.text(value + 0.002, j + offset, f"{value:.3f}", va="center", ha="left", fontsize=7, color=PALETTE["black"])
    ax.axvline(1.0, color=PALETTE["black"], linestyle=":", linewidth=1.0)
    ax.set_yticks(ys)
    ax.set_yticklabels(experiments)
    ax.set_xlabel("Fraction of pair-best-single IPC")
    ax.set_title("How far are methods from the pair-best ceiling?")
    ax.legend(fontsize=8, ncols=2, title="Split")
    ax.grid(True, axis="x", linestyle=":")
    fig.text(0.01, 0.01, "Caption: This summary measures distance from the pair-best single ceiling. Values below 1.0 mean the coordinator is still slower than the better of Pythia and SPP+PPF on that split.", ha="left", va="bottom", fontsize=8, color=PALETTE["black"], wrap=True)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
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
    colors = [PALETTE["blue"] if d >= 0 else PALETTE["magenta"] for d in deltas]
    fig, ax = plt.subplots(figsize=(7, max(3, 0.3 * len(labels))))
    ax.barh(labels, deltas, color=colors, edgecolor=PALETTE["black"], linewidth=0.4)
    ax.axvline(0.0, color=PALETTE["black"], linewidth=0.8)
    ax.set_xlabel("Δ IPC vs best single expert (%)")
    ax.set_title("MoP-lite per-trace win/loss vs best single expert")
    fig.text(0.01, 0.01, "Caption: Blue bars are trace-level wins, magenta bars are losses. This figure shows whether localized MoPLite wins are broad enough to outweigh the losses in aggregate.", ha="left", va="bottom", fontsize=8, color=PALETTE["black"], wrap=True)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


# -- Figure 4: single-expert winner profile + MoPLite -----------------------------

def fig_single_expert_profiles(rows: list[dict], out_path: Path) -> None:
    singles = [r for r in rows if r["experiment_kind"] == "single" and r.get("split_side") in {"train", "heldout"}]
    if not singles:
        skip_output(out_path, "no single-expert rows")
        return
    traces = ordered_traces(singles)
    split_for_trace = {r["trace"]: r.get("split_side", "unknown") for r in singles}
    best = {}
    runner_up = {}
    mop = {}
    for trace in traces:
        trace_rows = sorted([r for r in singles if r["trace"] == trace], key=lambda r: r["speedup_vs_baseline"], reverse=True)
        if not trace_rows:
            continue
        best[trace] = trace_rows[0]
        runner_up[trace] = trace_rows[1] if len(trace_rows) > 1 else None
        mop_rows = [r for r in rows if r["trace"] == trace and r["experiment"] == "MoPLite"]
        if mop_rows:
            mop[trace] = mop_rows[0]

    fig, ax = plt.subplots(figsize=(10, max(6, len(traces) * 0.35)))
    y = list(range(len(traces)))
    ax.scatter(
        [best[t]["speedup_vs_baseline"] for t in traces],
        y,
        s=70,
        c=[experiment_color(best[t]["experiment"]) for t in traces],
        edgecolors=PALETTE["black"],
        linewidths=0.5,
        zorder=3,
    )
    ax.scatter(
        [mop.get(t, {"speedup_vs_baseline": math.nan})["speedup_vs_baseline"] for t in traces],
        y,
        s=54,
        marker="s",
        c=PALETTE["magenta"],
        edgecolors=PALETTE["black"],
        linewidths=0.5,
        zorder=4,
    )
    for idx, trace in enumerate(traces):
        if runner_up[trace] is not None:
            ax.scatter(
                [runner_up[trace]["speedup_vs_baseline"]],
                [idx],
                s=40,
                facecolors=PALETTE["white"],
                edgecolors=experiment_color(runner_up[trace]["experiment"]),
                linewidths=1.2,
                zorder=2,
            )
    ax.axvline(1.0, color=PALETTE["black"], linestyle=":", linewidth=1.0)
    for idx in range(1, len(traces)):
        if split_for_trace[traces[idx - 1]] != split_for_trace[traces[idx]]:
            ax.axhline(idx - 0.5, color=PALETTE["light_grey"], linewidth=1.0)
    ax.set_yticks(y)
    ax.set_yticklabels([t[:30] for t in traces])
    ax.set_xlabel("IPC vs no-prefetch")
    ax.set_title("Which single expert wins where, and where does MoPLite land?")
    ax.grid(True, axis="x", linestyle=":")
    legend_handles = []
    for name in ["MLOP", "Pythia", "SMS", "SPP+PPF"]:
        legend_handles.append(plt.Line2D([0], [0], marker='o', color='none', markerfacecolor=experiment_color(name), markeredgecolor=PALETTE["black"], markersize=8, label=name))
    legend_handles.append(plt.Line2D([0], [0], marker='s', color='none', markerfacecolor=PALETTE["magenta"], markeredgecolor=PALETTE["black"], markersize=8, label='MoPLite'))
    legend_handles.append(plt.Line2D([0], [0], marker='o', color='none', markerfacecolor=PALETTE["white"], markeredgecolor=PALETTE["black"], markersize=7, label='Runner-up'))
    ax.legend(handles=legend_handles, fontsize=8, ncols=3)
    fig.text(0.01, 0.01, "Caption: Filled circles show the winning single prefetcher on each trace, hollow circles show the runner-up, and magenta squares show MoPLite. This makes it visible whether the router lands near the better expert, between the two experts, or below both of them.", ha="left", va="bottom", fontsize=8, color=PALETTE["black"], wrap=True)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


# -- Table: router ablation ------------------------------------------------------

def table_router_ablation(rows: list[dict], out_path: Path) -> None:
    by_experiment: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(lambda: {"vs_base": [], "vs_single": []})
    for r in rows:
        if r["experiment_kind"] not in {"router", "builtin"}:
            continue
        split = r["split_side"]
        by_experiment[(r["experiment"], split)]["vs_base"].append(r["speedup_vs_baseline"])
        by_experiment[(r["experiment"], split)]["vs_single"].append(r["speedup_vs_best_single"])

    lines = [
        "# Router / coordinator ablation",
        "",
        "Geometric mean of IPC speedup vs no-prefetch and vs the pair-best single expert, by split side.",
        "Reported only for (experiment, split) cells that contain runs.",
        "",
        "| Coordinator | Split | Runs | Geomean vs no-pref | Geomean vs pair-best single | Min vs pair-best | Max vs pair-best |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    if not by_experiment:
        lines.append("| _(no coordinator runs yet)_ | - | 0 | - | - | - | - |")
    for (experiment, split), payload in sorted(by_experiment.items()):
        values_base = payload["vs_base"]
        values_single = payload["vs_single"]
        gmean_base = geomean(values_base)
        gmean_single = geomean(values_single)
        lo = min(values_single) if values_single else float("nan")
        hi = max(values_single) if values_single else float("nan")
        lines.append(
            f"| {experiment} | {split} | {len(values_single)} | "
            f"{gmean_base:.4f} | {gmean_single:.4f} | {lo:.4f} | {hi:.4f} |"
        )
    out_path.write_text("\n".join(lines) + "\n")


# -- Table: expert pair ablation -------------------------------------------------

def table_expert_pair(rows: list[dict], out_path: Path) -> None:
    # Currently only one pair is in scope (Pythia + SPP+PPF). We emit a placeholder
    # row per pair observed, ready to extend when additional pairs are added.
    pairs: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(lambda: {"vs_base": [], "vs_single": []})
    for r in rows:
        if r["experiment"] != "MoPLite":
            continue
        key = (r.get("expert_0") or "?", r.get("expert_1") or "?")
        pairs[key]["vs_base"].append(r["speedup_vs_baseline"])
        pairs[key]["vs_single"].append(r["speedup_vs_best_single"])
    lines = [
        "# Expert-pair ablation (MoP-lite router only)",
        "",
        "| Expert 0 | Expert 1 | Runs | Geomean vs no-pref | Geomean vs pair-best single |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    if not pairs:
        lines.append("| - | - | 0 | - | - |")
    for (e0, e1), payload in sorted(pairs.items()):
        lines.append(
            f"| {e0} | {e1} | {len(payload['vs_single'])} | {geomean(payload['vs_base']):.4f} | {geomean(payload['vs_single']):.4f} |"
        )
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
    fig_speedup_summary       (rows, args.figures_dir / "ipc_speedup_summary.png")
    fig_mop_vs_reference_rows (rows, args.figures_dir / "mop_vs_reference_rows.png")
    (args.figures_dir / "ipc_speedup_vs_nopref.png").unlink(missing_ok=True)
    (args.figures_dir / "ipc_speedup_vs_best_single.png").unlink(missing_ok=True)
    fig_win_loss              (rows, args.figures_dir / "win_loss_mop_vs_best_single.png")
    fig_single_expert_profiles(rows, args.figures_dir / "single_expert_profiles.png")
    (args.figures_dir / "accuracy_vs_traffic.png").unlink(missing_ok=True)
    table_router_ablation     (rows, args.tables_dir / "router_ablation.md")
    table_expert_pair         (rows, args.tables_dir / "expert_pair_ablation.md")
    table_hardware_budget     (args.tables_dir / "hardware_budget.md")
    print(f"Figures: {args.figures_dir}")
    print(f"Tables:  {args.tables_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
