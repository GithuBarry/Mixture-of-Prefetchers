#!/usr/bin/env python3
"""Summarize a candidate router against a baseline router and pair-best single."""
from __future__ import annotations

import argparse
import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path


def geomean(values: list[float]) -> float:
    assert values, "No values for geomean"
    assert all(v > 0.0 and not math.isnan(v) for v in values), values
    return math.exp(statistics.fmean(math.log(v) for v in values))


def load_summary(path: Path) -> list[dict]:
    assert path.exists(), f"Summary CSV not found: {path}"
    rows = list(csv.DictReader(path.open()))
    assert rows, f"Summary CSV is empty: {path}"
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary_csv", type=Path)
    parser.add_argument("--candidate", default="MoPLiteGuarded")
    parser.add_argument("--baseline-router", default="MoPLite")
    parser.add_argument("--single", action="append", default=["Pythia", "SPP+PPF"])
    args = parser.parse_args()

    by_trace: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in load_summary(args.summary_csv):
        row = dict(row)
        row["ipc"] = float(row["ipc"])
        row["speedup_vs_baseline"] = float(row["speedup_vs_baseline"])
        by_trace[row["trace"]][row["experiment"]] = row

    required = {args.candidate, args.baseline_router, *args.single}
    missing = {
        trace: sorted(required - set(experiments))
        for trace, experiments in by_trace.items()
        if required - set(experiments)
    }
    assert not missing, f"Missing required rows: {missing}"

    candidate_vs_nopref: list[float] = []
    baseline_vs_nopref: list[float] = []
    candidate_vs_pairbest: list[float] = []
    candidate_vs_router: list[float] = []

    print("| Trace | Candidate vs no-pref | Baseline router vs no-pref | Candidate vs pair-best | Candidate / router |")
    print("| --- | ---: | ---: | ---: | ---: |")
    for trace in sorted(by_trace):
        rows = by_trace[trace]
        candidate = rows[args.candidate]
        baseline_router = rows[args.baseline_router]
        pair_best_ipc = max(rows[single]["ipc"] for single in args.single)
        cand_nopref = candidate["speedup_vs_baseline"]
        base_nopref = baseline_router["speedup_vs_baseline"]
        cand_pair = candidate["ipc"] / pair_best_ipc
        cand_router = candidate["ipc"] / baseline_router["ipc"]
        candidate_vs_nopref.append(cand_nopref)
        baseline_vs_nopref.append(base_nopref)
        candidate_vs_pairbest.append(cand_pair)
        candidate_vs_router.append(cand_router)
        print(f"| {trace} | {cand_nopref:.4f} | {base_nopref:.4f} | {cand_pair:.4f} | {cand_router:.4f} |")

    print()
    print(f"candidate_vs_no_pref_geomean={geomean(candidate_vs_nopref):.6f}")
    print(f"baseline_router_vs_no_pref_geomean={geomean(baseline_vs_nopref):.6f}")
    print(f"candidate_vs_pair_best_single_geomean={geomean(candidate_vs_pairbest):.6f}")
    print(f"candidate_vs_baseline_router_geomean={geomean(candidate_vs_router):.6f}")
    print(f"candidate_no_pref_wins={sum(v > 1.0 for v in candidate_vs_nopref)}/{len(candidate_vs_nopref)}")
    print(f"candidate_pair_best_wins={sum(v > 1.0 for v in candidate_vs_pairbest)}/{len(candidate_vs_pairbest)}")
    print(f"candidate_router_wins={sum(v > 1.0 for v in candidate_vs_router)}/{len(candidate_vs_router)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
