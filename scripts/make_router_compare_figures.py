#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
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
    "white": "#ffffff",
}

METHOD_COLOR = {
    "AthenaMAB": PALETTE["amber"],
    "WinnerTakeAll": PALETTE["purple"],
    "FixedSplit": PALETTE["blue"],
    "MoPLite": PALETTE["magenta"],
}

ACTION_LABEL = {0: "both off", 1: "SPP+PPF only", 2: "Pythia only", 3: "both on"}
ACTION_COLOR = {0: PALETTE["light_grey"], 1: PALETTE["purple"], 2: PALETTE["blue"], 3: PALETTE["magenta"]}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--results-dir", type=Path, action="append", required=True)
    p.add_argument("--out", type=Path, required=True)
    return p.parse_args()


def summarize_epoch_csv(path: Path) -> tuple[dict[str, float], Counter]:
    rows = list(csv.DictReader(path.open()))
    total = incl = nonzero_total = nonzero_incl = exact = 0
    action_counter: Counter = Counter()
    for row in rows:
        action = int(row["action"])
        useful0 = float(row["useful0"] or 0)
        useful1 = float(row["useful1"] or 0)
        chosen = {0: set(), 1: {1}, 2: {0}, 3: {0, 1}}[action]
        if useful0 <= 0 and useful1 <= 0:
            oracle = set()
        elif useful0 > useful1:
            oracle = {0}
        elif useful1 > useful0:
            oracle = {1}
        else:
            oracle = {0, 1}
        total += 1
        action_counter[action] += 1
        if chosen == oracle:
            exact += 1
        if oracle.issubset(chosen):
            incl += 1
        if oracle:
            nonzero_total += 1
            if oracle.issubset(chosen):
                nonzero_incl += 1
    return (
        {
            "oracle_included": incl / total if total else 0.0,
            "oracle_nonzero_included": nonzero_incl / nonzero_total if nonzero_total else 0.0,
            "exact_oracle": exact / total if total else 0.0,
        },
        action_counter,
    )


def main() -> int:
    args = parse_args()
    files = []
    for results_dir in args.results_dir:
        files.extend(sorted(results_dir.rglob("epoch_logs/*.csv")))
    assert files, f"No epoch logs found under {args.results_dir}"

    by_method_trace: dict[tuple[str, str], dict[str, float]] = {}
    action_mix: dict[str, Counter] = defaultdict(Counter)
    traces = set()
    methods = set()
    for path in files:
        stem = path.stem.replace(".core0", "")
        trace, method = stem.split("__", 1)
        stats, actions = summarize_epoch_csv(path)
        by_method_trace[(method, trace)] = stats
        action_mix[method].update(actions)
        traces.add(trace)
        methods.add(method)

    traces = sorted(traces)
    methods = [m for m in ["AthenaMAB", "WinnerTakeAll", "FixedSplit", "MoPLite"] if m in methods]

    fig, axes = plt.subplots(2, 1, figsize=(10, max(8, len(traces) * 0.45 + 3)), gridspec_kw={"height_ratios": [1.8, 1.2]})

    width = 0.18
    y = list(range(len(traces)))
    for offset_idx, method in enumerate(methods):
        vals = [by_method_trace[(method, trace)]["oracle_nonzero_included"] for trace in traces]
        axes[0].barh(
            [yy + (offset_idx - (len(methods) - 1) / 2) * width for yy in y],
            vals,
            height=width,
            color=METHOD_COLOR[method],
            edgecolor=PALETTE["black"],
            linewidth=0.4,
            label=method,
        )
    axes[0].axvline(1.0, color=PALETTE["black"], linestyle=":", linewidth=1.0)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(traces)
    axes[0].set_xlabel("Offline-better expert included on useful epochs")
    axes[0].set_title("Router decisions: did the action include the better expert?")
    axes[0].grid(True, axis="x", linestyle=":")
    axes[0].legend(ncols=2, fontsize=8)

    for idx, method in enumerate(methods):
        total = sum(action_mix[method].values())
        left = 0.0
        for action in [0, 2, 1, 3]:
            value = action_mix[method][action] / total if total else 0.0
            axes[1].barh(idx, value, left=left, color=ACTION_COLOR[action], edgecolor=PALETTE["black"], linewidth=0.4)
            left += value
    axes[1].set_yticks(range(len(methods)))
    axes[1].set_yticklabels(methods)
    axes[1].set_xlabel("Action share across criterion traces")
    axes[1].set_title("What did each router predict?")
    axes[1].grid(True, axis="x", linestyle=":")
    legend_handles = [plt.Line2D([0], [0], color=ACTION_COLOR[a], lw=8, label=ACTION_LABEL[a]) for a in [0, 2, 1, 3]]
    axes[1].legend(handles=legend_handles, ncols=2, fontsize=8)

    fig.text(
        0.01,
        0.01,
        "Caption: Top panel measures whether the chosen action at least included the offline-better expert on epochs where one expert was actually useful. Bottom panel shows the action mix itself. A router can rank experts well yet still underperform if it turns both experts off too often or fails to isolate the better expert.",
        ha="left",
        va="bottom",
        fontsize=8,
        color=PALETTE["black"],
        wrap=True,
    )
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=160)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
