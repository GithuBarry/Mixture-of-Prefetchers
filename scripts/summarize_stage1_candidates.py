#!/usr/bin/env python3
"""Summarize Stage 1 candidate result directories for the Stage 2 freeze."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


MOP_FAMILY = {"MoP-V0", "MoP-V1.1", "MoP-V1.2", "MoPLite", "MoPLiteGuarded", "ProbeThenWinner"}


def geomean(values: list[float]) -> float:
    assert values, "geomean needs at least one value"
    assert min(values) > 0, f"geomean got nonpositive value: {values}"
    return math.exp(sum(math.log(v) for v in values) / len(values))


def load_summary(path: Path) -> list[dict[str, str]]:
    summary_path = path / "summary.csv"
    assert summary_path.exists(), f"Missing {summary_path}"
    return list(csv.DictReader(summary_path.open()))


def load_manifest(path: Path) -> list[dict]:
    manifest_path = path / "manifest.jsonl"
    assert manifest_path.exists(), f"Missing {manifest_path}"
    return [json.loads(line) for line in manifest_path.read_text().splitlines() if line.strip()]


def pair_label(manifest: list[dict]) -> str:
    pairs = sorted({
        (row.get("expert_0"), row.get("expert_1"))
        for row in manifest
        if row.get("experiment_kind") in {"router", "builtin"}
    })
    pairs = [pair for pair in pairs if pair[0] and pair[1]]
    assert len(pairs) == 1, f"Expected one expert pair in manifest, got {pairs}"
    return f"{pairs[0][0]} + {pairs[0][1]}"


def action_mix(path: Path, experiment: str) -> tuple[float | None, float | None, float | None]:
    files = list((path / "runs").glob(f"*/epoch_logs/*__{experiment}.core0.csv"))
    if not files:
        return None, None, None
    counts: Counter[int] = Counter()
    total = 0
    for file in files:
        for row in csv.DictReader(file.open()):
            counts[int(row["action"])] += 1
            total += 1
    if total == 0:
        return None, None, None
    return counts[0] / total, counts[3] / total, (counts[1] + counts[2]) / total


def router_setting(manifest: list[dict], experiment: str, key: str) -> str:
    values = {
        row.get(key)
        for row in manifest
        if row.get("experiment") == experiment and row.get("experiment_kind") == "router"
    }
    values.discard(None)
    if not values:
        return ""
    assert len(values) == 1, f"Expected one {key} for {experiment}, got {values}"
    return str(next(iter(values)))


def summarize_dir(path: Path) -> list[dict]:
    rows = load_summary(path)
    manifest = load_manifest(path)
    pair = pair_label(manifest)
    by_trace: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in rows:
        by_trace[row["trace"]][row["experiment"]] = row
    experiments = sorted({row["experiment"] for row in rows})
    out: list[dict] = []
    for experiment in experiments:
        if experiment == "Baseline":
            continue
        values_base: list[float] = []
        values_best: list[float] = []
        between = 0
        closer = 0
        both_good = 0
        catastrophic = 0
        for trace, trace_rows in by_trace.items():
            row = trace_rows[experiment]
            val_base = float(row["speedup_vs_baseline"])
            val_best = float(row["speedup_vs_best_single"])
            values_base.append(val_base)
            values_best.append(val_best)
            catastrophic += val_best < 0.95

            expert_names = [
                name for name, item in trace_rows.items()
                if item["experiment_kind"] == "single"
            ]
            if len(expert_names) >= 2 and experiment in trace_rows:
                # The run summary defines pair-best over the routee singles, so infer
                # routees from manifest and use only those two for the between test.
                routees = pair.split(" + ")
                if all(name in trace_rows for name in routees):
                    r0 = float(trace_rows[routees[0]]["speedup_vs_baseline"])
                    r1 = float(trace_rows[routees[1]]["speedup_vs_baseline"])
                    both_good += r0 > 1.0 and r1 > 1.0
                    worst, best = sorted((r0, r1))
                    if worst <= val_base <= best:
                        between += 1
                        closer += abs(best - val_base) <= abs(val_base - worst)
        off_rate, both_rate, single_rate = action_mix(path, experiment)
        out.append({
            "result_dir": str(path),
            "pair": pair,
            "experiment": experiment,
            "n": len(values_base),
            "mop_total_budget": router_setting(manifest, experiment, "mop_total_budget"),
            "mop_one_shot_epochs": router_setting(manifest, experiment, "mop_one_shot_epochs"),
            "gm_vs_nopref": geomean(values_base),
            "gm_vs_pair_best": geomean(values_best),
            "wins_vs_nopref": sum(v > 1.0 for v in values_base),
            "catastrophic_vs_pair_best": catastrophic,
            "both_routees_gt_1": both_good,
            "between_routees": between,
            "closer_to_better": closer,
            "off_rate": off_rate,
            "both_on_rate": both_rate,
            "single_action_rate": single_rate,
        })
    return out


def fmt(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results_dir", type=Path, nargs="+")
    parser.add_argument("--only-mop-family", action="store_true")
    args = parser.parse_args()

    rows: list[dict] = []
    for path in args.results_dir:
        rows.extend(summarize_dir(path))
    if args.only_mop_family:
        rows = [row for row in rows if row["experiment"] in MOP_FAMILY]
    rows.sort(key=lambda row: (row["pair"], -row["gm_vs_pair_best"], row["experiment"]))

    columns = [
        "result_dir", "pair", "experiment", "n", "gm_vs_nopref", "gm_vs_pair_best",
        "mop_total_budget", "mop_one_shot_epochs",
        "wins_vs_nopref", "catastrophic_vs_pair_best", "both_routees_gt_1",
        "between_routees", "closer_to_better", "off_rate", "both_on_rate", "single_action_rate",
    ]
    print("| " + " | ".join(columns) + " |")
    print("| " + " | ".join("---" for _ in columns) + " |")
    for row in rows:
        print("| " + " | ".join(fmt(row[col]) for col in columns) + " |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
