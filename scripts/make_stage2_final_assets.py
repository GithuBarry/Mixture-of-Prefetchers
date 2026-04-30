#!/usr/bin/env python3
"""Build final OpenEvolve report tables and figures from raw run artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402


COLORS = {
    "orange": "#fe6100",
    "pink": "#dc267f",
    "purple": "#785ef0",
    "blue": "#648fff",
    "darkblue": "#3f6fd1",
    "black": "#000000",
    "white": "#ffffff",
    "lightgrey": "#d9d9d9",
}

METHOD_COLOR = {
    "MLOP": COLORS["blue"],
    "SPP+PPF": COLORS["purple"],
    "Manual router": COLORS["orange"],
    "OpenEvolve router": COLORS["pink"],
    "MoP-V1 manual router": COLORS["orange"],
    "MoP-V2 OpenEvolve router": COLORS["pink"],
    "MoP-V1.2": COLORS["orange"],
    "MoP-V1.3": COLORS["pink"],
    "best_expert": COLORS["darkblue"],
}

EVOLVE_MODEL_COLOR = {
    "GPT-5 mini": COLORS["pink"],
    "GPT-5.4": COLORS["purple"],
    "Sonnet 4.6": COLORS["blue"],
}

EVOLVE_MODEL_MARKER = {
    "GPT-5 mini": "o",
    "GPT-5.4": "s",
    "Sonnet 4.6": "^",
}


def geomean(values: list[float]) -> float:
    assert values
    assert min(values) > 0
    return math.exp(sum(math.log(v) for v in values) / len(values))


def bootstrap_geomean_ci(
    values: list[float],
    *,
    samples: int = 10_000,
    seed: int = 15740,
) -> tuple[float, float]:
    assert values
    rng = random.Random(seed)
    n = len(values)
    estimates = []
    for _ in range(samples):
        estimates.append(geomean([values[rng.randrange(n)] for _ in range(n)]))
    estimates.sort()
    return estimates[int(0.025 * samples)], estimates[int(0.975 * samples) - 1]


def format_ci(low: float, high: float, *, percent: bool = False) -> str:
    if percent:
        return f"[{100.0 * low:.1f}%, {100.0 * high:.1f}%]"
    return f"[{low:.3f}, {high:.3f}]"


def load_summary(path: Path) -> list[dict[str, str]]:
    summary = path / "summary.csv"
    assert summary.exists(), f"Missing {summary}"
    return list(csv.DictReader(summary.open()))


def by_trace(rows: list[dict[str, str]]) -> dict[str, dict[str, dict[str, str]]]:
    out: dict[str, dict[str, dict[str, str]]] = {}
    for row in rows:
        out.setdefault(row["trace"], {})[row["experiment"]] = row
    return out


def trace_speedups(result_dir: Path, experiment: str) -> list[float]:
    traces = by_trace(load_summary(result_dir))
    vals = [float(traces[trace][experiment]["speedup_vs_baseline"]) for trace in sorted(traces)]
    assert vals
    return vals


def trace_router_records(result_dir: Path, router: str) -> list[dict[str, float]]:
    traces = by_trace(load_summary(result_dir))
    records = []
    for trace in sorted(traces):
        trace_rows = traces[trace]
        r = float(trace_rows[router]["speedup_vs_baseline"])
        e0 = float(trace_rows["MLOP"]["speedup_vs_baseline"])
        e1 = float(trace_rows["SPP+PPF"]["speedup_vs_baseline"])
        pair_best = max(e0, e1)
        weaker = min(e0, e1)
        records.append({
            "router": r,
            "pair_best": pair_best,
            "weaker": weaker,
            "vs_pair_best": r / pair_best,
            "vs_weaker": r / weaker,
            "both_gt_1": float(e0 > 1.0 and e1 > 1.0),
        })
    assert records
    return records


def summarize_router(result_dir: Path, router: str) -> dict[str, float]:
    records = trace_router_records(result_dir, router)
    vs_base: list[float] = []
    vs_pair: list[float] = []
    vs_weaker: list[float] = []
    pair_best_vs_base: list[float] = []
    weaker_vs_base: list[float] = []
    beats_weaker = 0
    catastrophic = 0
    both_gt_1 = 0
    closer = 0
    for record in records:
        r = record["router"]
        pair_best = record["pair_best"]
        weaker = record["weaker"]
        vs_base.append(r)
        vs_pair.append(record["vs_pair_best"])
        vs_weaker.append(record["vs_weaker"])
        pair_best_vs_base.append(pair_best)
        weaker_vs_base.append(weaker)
        beats_weaker += r > weaker
        catastrophic += (r / pair_best) < 0.95
        both_gt_1 += int(record["both_gt_1"])
        closer += abs(pair_best - r) <= abs(r - weaker)
    router_ci = bootstrap_geomean_ci(vs_base)
    pair_best_ci = bootstrap_geomean_ci(pair_best_vs_base)
    pair_ratio_ci = bootstrap_geomean_ci(vs_pair)
    return {
        "n": float(len(records)),
        "gm_vs_nopref": geomean(vs_base),
        "gm_vs_nopref_ci_low": router_ci[0],
        "gm_vs_nopref_ci_high": router_ci[1],
        "gm_vs_pair_best": geomean(vs_pair),
        "gm_vs_pair_best_ci_low": pair_ratio_ci[0],
        "gm_vs_pair_best_ci_high": pair_ratio_ci[1],
        "gm_vs_weaker": geomean(vs_weaker),
        "pair_best_vs_nopref": geomean(pair_best_vs_base),
        "pair_best_vs_nopref_ci_low": pair_best_ci[0],
        "pair_best_vs_nopref_ci_high": pair_best_ci[1],
        "weaker_vs_nopref": geomean(weaker_vs_base),
        "beats_weaker": float(beats_weaker),
        "catastrophic": float(catastrophic),
        "both_routees_gt_1": float(both_gt_1),
        "closer_to_better": float(closer),
    }


def summarize_single(result_dir: Path, experiment: str) -> dict[str, float]:
    vals = trace_speedups(result_dir, experiment)
    ci = bootstrap_geomean_ci(vals)
    return {
        "n": float(len(vals)),
        "gm_vs_nopref": geomean(vals),
        "gm_vs_nopref_ci_low": ci[0],
        "gm_vs_nopref_ci_high": ci[1],
    }


def load_metric_json(row: dict[str, str]) -> dict:
    return json.loads(Path(row["metrics"]).read_text())


def summarize_instruction_check(result_dir: Path, router: str, label: str) -> dict[str, str]:
    rows = load_summary(result_dir)
    traces = by_trace(rows)
    instr_ratios: list[float] = []
    cycle_ratios: list[float] = []
    ipc_speedups: list[float] = []
    max_instr_delta = 0.0
    for trace_rows in traces.values():
        base = load_metric_json(trace_rows["Baseline"])
        routed = load_metric_json(trace_rows[router])
        base_instr = float(base["Core_0_total_instructions"])
        routed_instr = float(routed["Core_0_total_instructions"])
        base_cycles = float(base["Core_0_cycles"])
        routed_cycles = float(routed["Core_0_cycles"])
        instr_ratio = routed_instr / base_instr
        instr_ratios.append(instr_ratio)
        cycle_ratios.append(routed_cycles / base_cycles)
        ipc_speedups.append(float(trace_rows[router]["speedup_vs_baseline"]))
        max_instr_delta = max(max_instr_delta, abs(instr_ratio - 1.0))
    return {
        "evaluation_set": label,
        "n": str(len(traces)),
        "ipc_speedup_vs_prefetcher_off": f"{geomean(ipc_speedups):.3f}",
        "instruction_count_ratio_vs_prefetcher_off": f"{geomean(instr_ratios):.3f}",
        "cycle_count_ratio_vs_prefetcher_off": f"{geomean(cycle_ratios):.3f}",
        "max_instruction_ratio_delta": f"{max_instr_delta:.3f}",
    }


def metric_table(
    train_v12: Path,
    train_v13: Path,
    heldout_v12: Path,
    heldout_v13: Path,
) -> list[dict[str, str]]:
    rows = []
    specs = [
        ("training-split validation", "MoP-V1 manual router", train_v12, "MoP-V1.2"),
        ("training-split validation", "MoP-V2 OpenEvolve router", train_v13, "MoP-V1.3"),
        ("heldout", "MoP-V1 manual router", heldout_v12, "MoP-V1.2"),
        ("heldout", "MoP-V2 OpenEvolve router", heldout_v13, "MoP-V1.3"),
    ]
    for split, label, path, router in specs:
        metrics = summarize_router(path, router)
        rows.append({
            "split": split,
            "method": label,
            "n": str(int(metrics["n"])),
            "speedup_vs_prefetcher_off": f"{metrics['gm_vs_nopref']:.3f}",
            "speedup_95ci": format_ci(metrics["gm_vs_nopref_ci_low"], metrics["gm_vs_nopref_ci_high"]),
            "best_expert_speedup": f"{metrics['pair_best_vs_nopref']:.3f}",
            "best_expert_95ci": format_ci(metrics["pair_best_vs_nopref_ci_low"], metrics["pair_best_vs_nopref_ci_high"]),
            "percent_of_best_expert": f"{100.0 * metrics['gm_vs_pair_best']:.1f}%",
            "percent_of_best_expert_95ci": format_ci(
                metrics["gm_vs_pair_best_ci_low"],
                metrics["gm_vs_pair_best_ci_high"],
                percent=True,
            ),
            "beats_worse_prefetcher": f"{int(metrics['beats_weaker'])}/{int(metrics['n'])}",
            "below_95pct_of_best_expert": f"{int(metrics['catastrophic'])}/{int(metrics['n'])}",
            "closer_to_best_expert": f"{int(metrics['closer_to_better'])}/{int(metrics['n'])}",
            "both_prefetchers_beat_disabled": f"{int(metrics['both_routees_gt_1'])}/{int(metrics['n'])}",
        })
    for split, path in [("training-split validation", train_v13), ("heldout", heldout_v13)]:
        for experiment in ["MLOP", "SPP+PPF"]:
            metrics = summarize_single(path, experiment)
            rows.append({
                "split": split,
                "method": experiment,
                "n": str(int(metrics["n"])),
                "speedup_vs_prefetcher_off": f"{metrics['gm_vs_nopref']:.3f}",
                "speedup_95ci": format_ci(metrics["gm_vs_nopref_ci_low"], metrics["gm_vs_nopref_ci_high"]),
                "best_expert_speedup": "",
                "best_expert_95ci": "",
                "percent_of_best_expert": "",
                "percent_of_best_expert_95ci": "",
                "beats_worse_prefetcher": "",
                "below_95pct_of_best_expert": "",
                "closer_to_best_expert": "",
                "both_prefetchers_beat_disabled": "",
            })
    return rows


def write_markdown_table(rows: list[dict[str, str]], path: Path) -> None:
    cols = [
        "split",
        "method",
        "n",
        "speedup_vs_prefetcher_off",
        "speedup_95ci",
        "best_expert_speedup",
        "best_expert_95ci",
        "percent_of_best_expert",
        "percent_of_best_expert_95ci",
        "beats_worse_prefetcher",
        "below_95pct_of_best_expert",
        "closer_to_best_expert",
        "both_prefetchers_beat_disabled",
    ]
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row[col] for col in cols) + " |")
    path.write_text("\n".join(lines) + "\n")


def write_instruction_check_table(rows: list[dict[str, str]], path: Path) -> None:
    cols = [
        "evaluation_set",
        "n",
        "ipc_speedup_vs_prefetcher_off",
        "instruction_count_ratio_vs_prefetcher_off",
        "cycle_count_ratio_vs_prefetcher_off",
        "max_instruction_ratio_delta",
    ]
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row[col] for col in cols) + " |")
    path.write_text("\n".join(lines) + "\n")


def latest_checkpoint_info(run_dir: Path) -> dict:
    checkpoints = sorted(
        run_dir.glob("checkpoints/checkpoint_*/best_program_info.json"),
        key=lambda p: int(p.parent.name.rsplit("_", 1)[1]),
    )
    assert checkpoints, f"No checkpoints in {run_dir}"
    return json.loads(checkpoints[-1].read_text())


def best_checkpoint_info(run_dir: Path) -> dict:
    checkpoints = sorted(run_dir.glob("checkpoints/checkpoint_*/best_program_info.json"))
    assert checkpoints, f"No checkpoints in {run_dir}"
    infos = [json.loads(path.read_text()) for path in checkpoints]
    return max(infos, key=lambda info: float(info["metrics"]["combined_score"]))


def checkpoint_candidates(run_dir: Path) -> list[dict]:
    candidates: dict[str, dict] = {}
    for path in run_dir.glob("checkpoints/checkpoint_*/programs/*.json"):
        info = json.loads(path.read_text())
        metrics = info.get("metrics", {})
        if metrics.get("stage_passed") != 1.0 or float(metrics.get("n_traces", 0.0)) != 3.0:
            continue
        candidates[info["id"]] = info
    return sorted(candidates.values(), key=lambda info: (int(info["iteration_found"]), info["id"]))


def ledger_record_for_hash(ledger_path: Path, code_hash: str, stage: str) -> dict | None:
    records = [json.loads(line) for line in ledger_path.read_text().splitlines() if line.strip()]
    matches = [r for r in records if r.get("code_hash") == code_hash and r.get("stage") == stage]
    if not matches:
        return None
    return matches[-1]


def required_ledger_record_for_hash(ledger_path: Path, code_hash: str, stage: str) -> dict:
    record = ledger_record_for_hash(ledger_path, code_hash, stage)
    assert record is not None, f"Missing {stage} record for {code_hash} in {ledger_path}"
    return record


def record_speedup_ci(record: dict) -> tuple[float, float]:
    result_dir = Path(record["result_dir"])
    router = record["policy"]["router"]
    return bootstrap_geomean_ci(trace_speedups(result_dir, router), seed=15740 + len(router) + len(record["stage"]))


def ledger_record_for_metrics(ledger_path: Path, metrics: dict, stage: str) -> dict | None:
    records = [json.loads(line) for line in ledger_path.read_text().splitlines() if line.strip()]
    candidates = [r for r in records if r.get("stage") == stage and r.get("metrics", {}).get("stage_passed") == 1.0]
    for record in reversed(candidates):
        record_metrics = record["metrics"]
        keys = ["gm_vs_pair_best", "gm_vs_nopref", "gm_vs_weaker", "combined_score"]
        if all(abs(float(record_metrics[key]) - float(metrics[key])) < 1e-12 for key in keys):
            return record
    return None


def scale_model_rows(ledger_path: Path, scale_runs: list[tuple[str, Path]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for model, path in scale_runs:
        latest = latest_checkpoint_info(path)
        best = best_checkpoint_info(path)
        metrics = best["metrics"]
        stage1_record = ledger_record_for_metrics(ledger_path, metrics, "stage1")
        code_hash = stage1_record.get("code_hash", "") if stage1_record else ""
        confirmed = ledger_record_for_hash(ledger_path, code_hash, "stage2") if code_hash else None
        confirmed_metrics = confirmed["metrics"] if confirmed else None
        quick_ci = record_speedup_ci(stage1_record) if stage1_record else None
        confirmed_ci = record_speedup_ci(confirmed) if confirmed else None
        screen_nopref = float(metrics["gm_vs_nopref"])
        screen_pair_best_ratio = float(metrics["gm_vs_pair_best"])
        confirmed_nopref = float(confirmed_metrics["gm_vs_nopref"]) if confirmed_metrics else None
        confirmed_pair_best_ratio = float(confirmed_metrics["gm_vs_pair_best"]) if confirmed_metrics else None
        rows.append({
            "model": model,
            "iterations_seen": str(int(latest["current_iteration"])),
            "best_screen_iter": str(int(best["iteration"])),
            "quick_eval_speedup_vs_prefetcher_off": f"{screen_nopref:.3f}",
            "quick_eval_speedup_95ci": format_ci(*quick_ci) if quick_ci else "",
            "quick_eval_best_expert_speedup": f"{screen_nopref / screen_pair_best_ratio:.3f}",
            "quick_eval_percent_of_best_expert": f"{100.0 * screen_pair_best_ratio:.1f}%",
            "quick_eval_weighted_score": f"{float(metrics['combined_score']):.3f}",
            "wider_eval_speedup_vs_prefetcher_off": f"{confirmed_nopref:.3f}" if confirmed_nopref else "",
            "wider_eval_speedup_95ci": format_ci(*confirmed_ci) if confirmed_ci else "",
            "wider_eval_best_expert_speedup": (
                f"{confirmed_nopref / confirmed_pair_best_ratio:.3f}"
                if confirmed_nopref and confirmed_pair_best_ratio
                else ""
            ),
            "wider_eval_percent_of_best_expert": f"{100.0 * confirmed_pair_best_ratio:.1f}%" if confirmed_pair_best_ratio else "",
            "wider_eval_weighted_score": f"{float(confirmed_metrics['combined_score']):.3f}" if confirmed_metrics else "",
            "openevolve_output_dir": str(path),
            "evaluator_result_dir": f"results/stage2_openevolve/stage1/{code_hash}" if code_hash else "",
            "wider_evaluator_result_dir": confirmed["result_dir"] if confirmed else "",
        })
    return rows


def write_scale_model_table(rows: list[dict[str, str]], path: Path) -> None:
    cols = [
        "model",
        "iterations_seen",
        "best_screen_iter",
        "quick_eval_speedup_vs_prefetcher_off",
        "quick_eval_speedup_95ci",
        "quick_eval_best_expert_speedup",
        "quick_eval_percent_of_best_expert",
        "quick_eval_weighted_score",
        "wider_eval_speedup_vs_prefetcher_off",
        "wider_eval_speedup_95ci",
        "wider_eval_best_expert_speedup",
        "wider_eval_percent_of_best_expert",
        "wider_eval_weighted_score",
        "openevolve_output_dir",
        "evaluator_result_dir",
        "wider_evaluator_result_dir",
    ]
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row[col] for col in cols) + " |")
    path.write_text("\n".join(lines) + "\n")


def format_policy_value(value: object) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(f"{float(v):.2g}" for v in value) + "]"
    return str(value)


def policy_for_result(row: dict[str, str], ledger_path: Path) -> dict:
    code_hash = Path(row["evaluator_result_dir"]).name
    record = ledger_record_for_hash(ledger_path, code_hash, "stage2")
    if record is None:
        record = ledger_record_for_hash(ledger_path, code_hash, "stage1")
    assert record is not None, f"Missing policy record for {code_hash}"
    return record["policy"]


def policy_summary_rows(scale_rows: list[dict[str, str]], ledger_path: Path) -> list[dict[str, str]]:
    rows = [
        {
            "name": "MoP-V1",
            "source": "manual reference",
            "budget": "8192",
            "sticky_margin": "none",
            "accuracy_floor": "30",
            "min_budget_share": "10",
            "weights": "[1.0, 0.5, 1.0]",
            "wider_speedup": "",
            "final_train_speedup": "1.048",
            "heldout_speedup": "0.998",
        },
        {
            "name": "MoP-V2",
            "source": "selected GPT-5.4-mini plus GPT-5.4-nano/local-grid policy",
            "budget": "9216",
            "sticky_margin": "3%",
            "accuracy_floor": "30",
            "min_budget_share": "10",
            "weights": "[1.0, 0.55, 1.0]",
            "wider_speedup": "1.089",
            "final_train_speedup": "1.066",
            "heldout_speedup": "1.003",
        },
    ]
    for row in scale_rows:
        policy = policy_for_result(row, ledger_path)
        rows.append({
            "name": f"V2 candidate from {row['model']}",
            "source": "later model comparison sweep",
            "budget": format_policy_value(policy["mop_total_budget"]),
            "sticky_margin": f"{format_policy_value(policy['mop_sticky_margin_pct'])}%",
            "accuracy_floor": format_policy_value(policy["mop_accuracy_floor"]),
            "min_budget_share": format_policy_value(policy["mop_guarded_min_budget_share"]),
            "weights": format_policy_value(policy["mop_score_weights"]),
            "wider_speedup": row["wider_eval_speedup_vs_prefetcher_off"],
            "final_train_speedup": "",
            "heldout_speedup": "",
        })
    return rows


def write_policy_summary_table(rows: list[dict[str, str]], path: Path) -> None:
    cols = [
        "name",
        "source",
        "budget",
        "sticky_margin",
        "accuracy_floor",
        "min_budget_share",
        "weights",
        "wider_speedup",
        "final_train_speedup",
        "heldout_speedup",
    ]
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row[col] for col in cols) + " |")
    path.write_text("\n".join(lines) + "\n")


def setup_plot() -> None:
    plt.rcParams.update({
        "figure.facecolor": COLORS["white"],
        "axes.facecolor": COLORS["white"],
        "axes.edgecolor": COLORS["black"],
        "axes.labelcolor": COLORS["black"],
        "xtick.color": COLORS["black"],
        "ytick.color": COLORS["black"],
        "grid.color": COLORS["lightgrey"],
        "grid.linewidth": 0.6,
        "font.size": 10,
    })


def wrap_trace_label(trace: str, width: int = 34) -> str:
    label = trace.replace(".length_250M", "")
    if len(label) <= width:
        return label
    separators = [".", "_", "-"]
    midpoint = len(label) // 2
    candidates = [
        idx
        for idx, char in enumerate(label)
        if char in separators and abs(idx - midpoint) <= width // 2
    ]
    split_at = min(candidates, key=lambda idx: abs(idx - midpoint)) if candidates else width
    left = label[:split_at].rstrip("._-")
    right = label[split_at + 1 :].lstrip("._-")
    if len(right) > width:
        right = right[: width - 1] + "..."
    return f"{left}\n{right}"


def plot_v1_v2_trace_delta(
    train_v12: Path,
    train_v13: Path,
    heldout_v12: Path,
    heldout_v13: Path,
    out_path: Path,
) -> None:
    setup_plot()
    panels = [
        ("13 training traces", by_trace(load_summary(train_v12)), by_trace(load_summary(train_v13)), "MoP-V1.2", "MoP-V1.3"),
        ("7 heldout traces", by_trace(load_summary(heldout_v12)), by_trace(load_summary(heldout_v13)), "MoP-V1.2", "MoP-V1.3"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(14.8, 6.6), sharex=True)
    for ax, (title, before, after, before_key, after_key) in zip(axes, panels, strict=True):
        traces = sorted(set(before) & set(after))
        rows = []
        for trace in traces:
            v1 = float(before[trace][before_key]["speedup_vs_baseline"])
            v2 = float(after[trace][after_key]["speedup_vs_baseline"])
            rows.append((trace, v1, v2, v2 - v1))
        rows.sort(key=lambda item: item[3])
        y = list(range(len(rows)))
        colors = [METHOD_COLOR["OpenEvolve router"] if delta >= 0 else METHOD_COLOR["MoP-V1 manual router"] for _, _, _, delta in rows]
        ax.barh(y, [delta for _, _, _, delta in rows], color=colors, edgecolor=COLORS["black"], linewidth=0.5)
        ax.axvline(0.0, color=COLORS["black"], linestyle=":", linewidth=1.0)
        ax.set_yticks(y)
        ax.set_yticklabels([wrap_trace_label(trace, width=28) for trace, _, _, _ in rows], fontsize=8)
        ax.set_title(title)
        ax.set_xlabel("MoP-V2 speedup minus MoP-V1 speedup")
        ax.grid(True, axis="x", linestyle=":")
        ax.set_xlim(-0.055, 0.178)
        label_x = 0.164
        for yi, (_, v1, v2, delta) in zip(y, rows, strict=True):
            ax.text(
                label_x,
                yi,
                f"{v1:.3f}->{v2:.3f}",
                va="center",
                ha="right",
                fontsize=7,
                bbox={"facecolor": COLORS["white"], "edgecolor": "none", "pad": 0.8, "alpha": 0.82},
            )
    handles = [
        Line2D([0], [0], color=METHOD_COLOR["OpenEvolve router"], linewidth=8, label="MoP-V2 faster than MoP-V1"),
        Line2D([0], [0], color=METHOD_COLOR["MoP-V1 manual router"], linewidth=8, label="MoP-V1 faster than MoP-V2"),
    ]
    fig.legend(handles=handles, frameon=False, ncols=2, loc="lower center", bbox_to_anchor=(0.5, 0.04))
    fig.suptitle("Per-trace change from MoP-V1 to MoP-V2", y=0.98)
    fig.text(
        0.02,
        0.012,
        "Each label shows speedup over disabled prefetching before and after OpenEvolve. Positive bars mean MoP-V2 improved that trace.",
        ha="left",
        va="bottom",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.10, 1, 0.94))
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_pre_post(rows: list[dict[str, str]], out_path: Path) -> None:
    setup_plot()
    router_rows = [r for r in rows if r["method"] in {"MoP-V1 manual router", "MoP-V2 OpenEvolve router"}]
    splits = ["training-split validation", "heldout"]
    methods = ["MoP-V1 manual router", "MoP-V2 OpenEvolve router"]
    fig, ax = plt.subplots(figsize=(10, 4.8))
    width = 0.34
    cap_label_done = False
    for i, split in enumerate(splits):
        split_rows = [r for r in router_rows if r["split"] == split]
        cap_row = next(r for r in split_rows if r["method"] == "MoP-V2 OpenEvolve router")
        cap = float(cap_row["best_expert_speedup"])
        ax.hlines(cap, i - 0.32, i + 0.32, color=METHOD_COLOR["best_expert"], linewidth=2.8, zorder=5)
        ax.scatter(
            [i],
            [cap],
            marker="D",
            s=58,
            facecolor=METHOD_COLOR["best_expert"],
            edgecolor=METHOD_COLOR["best_expert"],
            linewidth=0.7,
            label="best expert" if not cap_label_done else None,
            zorder=6,
        )
        ax.text(i, cap + 0.006, f"best {cap:.3f}", ha="center", va="bottom", fontsize=8)
        cap_label_done = True
        for j, method in enumerate(methods):
            row = next(r for r in split_rows if r["method"] == method)
            value = float(row["speedup_vs_prefetcher_off"])
            x = i + (j - 0.5) * width
            ax.bar(
                x,
                value,
                width=width,
                color=METHOD_COLOR[method],
                alpha=0.65 if method == "MoP-V1 manual router" else 1.0,
                edgecolor=COLORS["black"],
                hatch="//" if method == "MoP-V1 manual router" else None,
                linewidth=0.8,
                label=method if i == 0 else None,
            )
            ax.text(x, value + 0.006, f"{value:.3f}", ha="center", va="bottom", fontsize=8)
    ax.axhline(1.0, color=COLORS["black"], linestyle=":", linewidth=1.0, label="prefetcher off")
    ax.set_xticks(range(len(splits)))
    ax.set_xticklabels(["13-trace\ntraining-split validation", "7-trace\nheldout"])
    ax.set_ylabel("Geomean IPC speedup vs disabled prefetching")
    ax.set_title("Router performance: MoP-V1 manual to MoP-V2 OpenEvolve")
    ax.set_ylim(0.96, 1.12)
    ax.grid(True, axis="y", linestyle=":")
    ax.legend(frameon=False, loc="upper right", ncols=2)
    fig.text(
        0.02,
        0.01,
        "Baseline: disabled prefetching at 1.000x. Dark-blue diamond/line: per-trace best expert before geomean.",
        ha="left",
        va="bottom",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_heldout_trace_profile(heldout_v12: Path, heldout_v13: Path, out_path: Path) -> None:
    setup_plot()
    manual_traces = by_trace(load_summary(heldout_v12))
    traces = by_trace(load_summary(heldout_v13))
    ordered = sorted(traces)
    base_y = list(range(len(ordered)))
    lane_offsets = {
        "MLOP": 0.27,
        "SPP+PPF": 0.09,
        "MoP-V1.2": -0.09,
        "MoP-V1.3": -0.27,
    }
    method_order = ["MLOP", "SPP+PPF", "MoP-V1.2", "MoP-V1.3"]
    fig, ax = plt.subplots(figsize=(12.8, 6.8))
    xmin = 0.68
    bar_height = 0.14
    method_rows = {
        "MLOP": traces,
        "SPP+PPF": traces,
        "MoP-V1.2": manual_traces,
        "MoP-V1.3": traces,
    }
    method_labels = {
        "MLOP": "Expert 1: MLOP",
        "SPP+PPF": "Expert 2: SPP+PPF",
        "MoP-V1.2": "MoP-V1 manual router",
        "MoP-V1.3": "MoP-V2 OpenEvolve router",
    }
    method_styles = {
        "MLOP": (COLORS["blue"], 0.95),
        "SPP+PPF": (COLORS["blue"], 0.50),
        "MoP-V1.2": (METHOD_COLOR["MoP-V1.2"], 0.90),
        "MoP-V1.3": (METHOD_COLOR["MoP-V1.3"], 0.90),
    }
    for method in method_order:
        rows_by_trace = method_rows[method]
        xs = [float(rows_by_trace[t][method]["speedup_vs_baseline"]) for t in ordered]
        ys = [yi + lane_offsets[method] for yi in base_y]
        color, alpha = method_styles[method]
        ax.barh(
            ys,
            [x_value - xmin for x_value in xs],
            left=xmin,
            height=bar_height,
            color=color,
            edgecolor=COLORS["black"],
            linewidth=0.45,
            alpha=alpha,
            label=method_labels[method],
        )
        for x_value, y_value in zip(xs, ys, strict=True):
            ax.text(x_value + 0.004, y_value, f"{x_value:.3f}", va="center", ha="left", fontsize=7)
    for yi, t in enumerate(ordered):
        values = [
            float(traces[t]["MLOP"]["speedup_vs_baseline"]),
            float(traces[t]["SPP+PPF"]["speedup_vs_baseline"]),
            float(manual_traces[t]["MoP-V1.2"]["speedup_vs_baseline"]),
            float(traces[t]["MoP-V1.3"]["speedup_vs_baseline"]),
        ]
        ax.hlines(yi, xmin, max(values), color=COLORS["lightgrey"], linewidth=0.8, zorder=0)
    ax.axvline(1.0, color=COLORS["black"], linestyle=":", linewidth=1.0)
    ax.set_yticks(base_y)
    ax.set_yticklabels([wrap_trace_label(t) for t in ordered])
    ax.set_xlabel("IPC speedup vs disabled prefetching")
    ax.set_title("Heldout trace profile: expert complementarity and router placement")
    ax.set_xlim(xmin, 1.38)
    ax.grid(True, axis="x", linestyle=":")
    ax.legend(frameon=False, ncols=4, loc="upper center", bbox_to_anchor=(0.5, -0.13))
    fig.text(
        0.02,
        0.01,
        "Each trace row is ordered top-to-bottom: Expert 1, Expert 2, MoP-V1, and MoP-V2. Black dotted line is disabled prefetching at 1.000x.",
        ha="left",
        va="bottom",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.14, 1, 1))
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def router_behavior_totals(result_dir: Path, router: str) -> dict[str, float]:
    rows = [row for row in load_summary(result_dir) if row["experiment"] == router]
    assert rows, f"Missing router {router} in {result_dir}"
    totals = {
        "selected_mlop": sum(float(row["pref0_selected_epochs"]) for row in rows),
        "selected_spp": sum(float(row["pref1_selected_epochs"]) for row in rows),
        "budget_mlop": sum(float(row["pref0_budget_total"]) for row in rows),
        "budget_spp": sum(float(row["pref1_budget_total"]) for row in rows),
        "useful_mlop": sum(float(row["pref0_useful_total"]) for row in rows),
        "useful_spp": sum(float(row["pref1_useful_total"]) for row in rows),
    }
    return totals


def share_pair(totals: dict[str, float], left_key: str, right_key: str) -> tuple[float, float]:
    left = totals[left_key]
    right = totals[right_key]
    denom = left + right
    if denom <= 0:
        return 0.0, 0.0
    return left / denom, right / denom


def plot_routing_behavior_stats(
    train_v12: Path,
    train_v13: Path,
    heldout_v12: Path,
    heldout_v13: Path,
    out_path: Path,
) -> None:
    setup_plot()
    specs = [
        ("Train MoP-V1", router_behavior_totals(train_v12, "MoP-V1.2")),
        ("Train MoP-V2", router_behavior_totals(train_v13, "MoP-V1.3")),
        ("Heldout MoP-V1", router_behavior_totals(heldout_v12, "MoP-V1.2")),
        ("Heldout MoP-V2", router_behavior_totals(heldout_v13, "MoP-V1.3")),
    ]
    panels = [
        ("Selected epochs", "selected_mlop", "selected_spp"),
        ("Budget allocation", "budget_mlop", "budget_spp"),
        ("Useful prefetches", "useful_mlop", "useful_spp"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.8), sharey=True)
    y = list(range(len(specs)))
    for ax, (title, mlop_key, spp_key) in zip(axes, panels, strict=True):
        mlop_shares = []
        spp_shares = []
        for _, totals in specs:
            mlop_share, spp_share = share_pair(totals, mlop_key, spp_key)
            mlop_shares.append(mlop_share)
            spp_shares.append(spp_share)
        ax.barh(y, mlop_shares, color=COLORS["blue"], edgecolor=COLORS["black"], linewidth=0.6, label="MLOP")
        ax.barh(
            y,
            spp_shares,
            left=mlop_shares,
            color=COLORS["blue"],
            alpha=0.45,
            edgecolor=COLORS["black"],
            linewidth=0.6,
            label="SPP+PPF",
        )
        for yi, mlop_share, spp_share in zip(y, mlop_shares, spp_shares, strict=True):
            if mlop_share >= 0.12:
                ax.text(mlop_share / 2, yi, f"{mlop_share:.0%}", ha="center", va="center", fontsize=8)
            if spp_share >= 0.12:
                ax.text(mlop_share + spp_share / 2, yi, f"{spp_share:.0%}", ha="center", va="center", fontsize=8)
        ax.set_title(title)
        ax.set_xlim(0, 1)
        ax.set_xlabel("Share of recorded router activity")
        ax.grid(True, axis="x", linestyle=":")
    axes[0].set_yticks(y)
    axes[0].set_yticklabels([label for label, _ in specs])
    axes[0].invert_yaxis()
    handles = [
        Line2D([0], [0], color=COLORS["blue"], linewidth=8, label="Expert 1: MLOP"),
        Line2D([0], [0], color=COLORS["blue"], alpha=0.45, linewidth=8, label="Expert 2: SPP+PPF"),
    ]
    fig.legend(handles=handles, frameon=False, ncols=2, loc="lower center", bbox_to_anchor=(0.5, 0.055))
    fig.suptitle("Routing behavior stats: MoP-V1 manual router to MoP-V2 OpenEvolve router", y=0.98)
    fig.text(
        0.02,
        0.012,
        "Shares are aggregated from final run summaries. MoP-V1 and MoP-V2 use the same expert order: MLOP first, SPP+PPF second.",
        ha="left",
        va="bottom",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.16, 1, 0.94))
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_scale_model_comparison(
    rows: list[dict[str, str]],
    out_path: Path,
    scale_runs: list[tuple[str, Path]],
    active_screen_nopref: float,
    active_screen_cap: float,
    active_confirm_nopref: float,
    active_confirm_cap: float,
) -> None:
    setup_plot()
    _ = rows
    model_colors = EVOLVE_MODEL_COLOR
    fig = plt.figure(figsize=(12.8, 6.4))
    grid = fig.add_gridspec(
        3,
        2,
        height_ratios=[1.0, 4.0, 0.85],
        width_ratios=[3.2, 1.0],
        hspace=0.08,
        wspace=0.24,
    )
    ax_top = fig.add_subplot(grid[0, 0])
    ax = fig.add_subplot(grid[1, 0], sharex=ax_top)
    ax_low = fig.add_subplot(grid[2, 0], sharex=ax_top)
    ax_right = fig.add_subplot(grid[:, 1])
    all_screen_y: list[float] = []
    for label, run_dir in scale_runs:
        candidates = checkpoint_candidates(run_dir)
        xs = [int(candidate["iteration_found"]) for candidate in candidates]
        ys = [float(candidate["metrics"]["gm_vs_nopref"]) for candidate in candidates]
        all_screen_y.extend(ys)
        ax.scatter(
            xs,
            ys,
            marker=EVOLVE_MODEL_MARKER[label],
            s=24,
            color=model_colors[label],
            alpha=0.22,
            edgecolor="none",
            label="_nolegend_",
        )
        ax_low.scatter(
            xs,
            ys,
            marker=EVOLVE_MODEL_MARKER[label],
            s=24,
            color=model_colors[label],
            alpha=0.22,
            edgecolor="none",
            label="_nolegend_",
        )
        score_incumbent_points: list[tuple[int, float]] = []
        ipc_best_points: list[tuple[int, float]] = []
        best_score = -float("inf")
        score_incumbent_speedup = float("nan")
        best_ipc_speedup = -float("inf")
        for candidate in candidates:
            candidate_speedup = float(candidate["metrics"]["gm_vs_nopref"])
            score = float(candidate["metrics"]["combined_score"])
            if score >= best_score:
                best_score = score
                score_incumbent_speedup = candidate_speedup
            best_ipc_speedup = max(best_ipc_speedup, candidate_speedup)
            iteration = int(candidate["iteration_found"])
            score_incumbent_points.append((iteration, score_incumbent_speedup))
            ipc_best_points.append((iteration, best_ipc_speedup))
        if score_incumbent_points:
            ax.step(
                [point[0] for point in score_incumbent_points],
                [point[1] for point in score_incumbent_points],
                where="post",
                color=model_colors[label],
                linewidth=1.5,
                linestyle="--",
                alpha=0.45,
                label="_nolegend_",
            )
            ax.step(
                [point[0] for point in ipc_best_points],
                [point[1] for point in ipc_best_points],
                where="post",
                color=model_colors[label],
                linewidth=2.2,
                label="_nolegend_",
            )
    ax_top.axhline(
        active_screen_cap,
        color=METHOD_COLOR["best_expert"],
        linewidth=2.0,
        label="_nolegend_",
    )
    ax.axhline(active_screen_nopref, color=METHOD_COLOR["OpenEvolve router"], linestyle="--", linewidth=1.8, label="_nolegend_")
    ax_low.set_xlabel("OpenEvolve iteration", labelpad=10)
    ax.set_ylabel("3-trace geomean IPC speedup vs disabled prefetching")
    ax_top.set_title("OpenEvolve search trajectory by model")
    ax_top.set_ylim(max(1.085, active_screen_cap - 0.010), active_screen_cap + 0.006)
    if all_screen_y:
        y_max = min(1.052, max(max(all_screen_y), active_screen_nopref) + 0.006)
        ax.set_ylim(1.025, max(y_max, 1.040))
        ax_low.set_ylim(max(1.010, min(all_screen_y) - 0.002), 1.015)
    ax_top.spines["bottom"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax_low.spines["top"].set_visible(False)
    ax_top.tick_params(labelbottom=False, bottom=False)
    ax.tick_params(labelbottom=False, bottom=False)
    ax_top.grid(True, axis="y", linestyle=":")
    break_kwargs = dict(marker=[(-1, -0.5), (1, 0.5)], markersize=8, linestyle="none", color=COLORS["black"], mec=COLORS["black"], mew=1, clip_on=False)
    ax_top.plot([0, 1], [0, 0], transform=ax_top.transAxes, **break_kwargs)
    ax.plot([0, 1], [1, 1], transform=ax.transAxes, **break_kwargs)
    ax.plot([0, 1], [0, 0], transform=ax.transAxes, **break_kwargs)
    ax_low.plot([0, 1], [1, 1], transform=ax_low.transAxes, **break_kwargs)
    ax.text(
        0.99,
        0.62,
        f"best expert {active_screen_cap:.3f}x",
        transform=ax_top.transAxes,
        ha="right",
        va="center",
        fontsize=8,
        color=COLORS["black"],
    )
    ax.text(
        0.01,
        0.08,
        "prefetcher off 1.000x",
        transform=ax_low.transAxes,
        ha="left",
        va="bottom",
        fontsize=8,
        color=COLORS["black"],
    )
    ax.grid(True, axis="y", linestyle=":")
    ax_low.grid(True, axis="y", linestyle=":")
    labels = [row["model"] for row in rows]
    quick = [float(row["quick_eval_speedup_vs_prefetcher_off"]) for row in rows]
    wider = [
        float(row["wider_eval_speedup_vs_prefetcher_off"]) if row["wider_eval_speedup_vs_prefetcher_off"] else float("nan")
        for row in rows
    ]
    x = list(range(len(labels)))
    ax_right.scatter(x, quick, marker="o", s=54, color=[model_colors[label] for label in labels], label="3-trace quick eval")
    for xi, value, label in zip(x, wider, labels, strict=True):
        if math.isnan(value):
            ax_right.scatter(xi, quick[xi] + 0.001, marker="x", s=60, color=model_colors[label], linewidth=2.0)
            ax_right.text(xi, quick[xi] + 0.003, "quick\nonly", ha="center", va="bottom", fontsize=8)
        else:
            ax_right.scatter(xi, value, marker="^", s=64, color=model_colors[label])
    ax_right.axhline(active_confirm_nopref, color=METHOD_COLOR["OpenEvolve router"], linestyle="--", linewidth=1.8)
    ax_right.set_xticks(x)
    ax_right.set_xticklabels(["GPT-5\nmini", "GPT-5.4", "Sonnet\n4.6"])
    ax_right.set_title("Wider validation")
    finite_wider = [value for value in wider if not math.isnan(value)]
    panel_values = quick + finite_wider + [active_confirm_nopref]
    if panel_values:
        ax_right.set_ylim(max(1.0, min(panel_values) - 0.006), max(panel_values) + 0.006)
    ax_right.text(
        0.98,
        0.96,
        f"best expert {active_confirm_cap:.3f}x",
        transform=ax_right.transAxes,
        ha="right",
        va="top",
        fontsize=8,
        color=COLORS["black"],
    )
    ax_right.text(
        0.05,
        0.04,
        "off 1.000x",
        transform=ax_right.transAxes,
        ha="left",
        va="bottom",
        fontsize=8,
        color=COLORS["black"],
    )
    ax_right.grid(True, axis="y", linestyle=":")
    handles = [
        Line2D(
            [0],
            [0],
            color=model_colors[label],
            marker=EVOLVE_MODEL_MARKER[label],
            linewidth=2.0,
            markersize=6,
            label=label,
        )
        for label in model_colors
    ]
    handles.extend([
        Line2D([0], [0], color=COLORS["lightgrey"], linestyle="--", linewidth=2.0, label="score-selected incumbent IPC"),
        Line2D([0], [0], color=COLORS["black"], linestyle="-", linewidth=2.0, label="best IPC seen so far"),
        Line2D([0], [0], color=METHOD_COLOR["OpenEvolve router"], linestyle="--", linewidth=2.0, label="selected MoP-V2"),
        Line2D([0], [0], color=METHOD_COLOR["best_expert"], linewidth=2.0, label="best expert"),
    ])
    fig.legend(
        handles=handles,
        frameon=False,
        ncols=4,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.115),
        columnspacing=1.3,
        handlelength=2.0,
    )
    fig.text(
        0.02,
        0.025,
        f"Faint points are candidates. Faint dashed lines show score-selected incumbent IPC. Solid lines show best IPC seen so far. Selected MoP-V2: {active_confirm_nopref:.3f}x.",
        ha="left",
        va="bottom",
        fontsize=8,
    )
    fig.subplots_adjust(left=0.08, right=0.98, top=0.90, bottom=0.32, wspace=0.24, hspace=0.08)
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-v12", type=Path, default=Path("results/stage2_openevolve/comparators/stage3_v12_current_20260429"))
    parser.add_argument("--train-v13", type=Path, default=Path("results/stage2_openevolve/stage3/a52ed8a4151ad6cc"))
    parser.add_argument("--heldout-v12", type=Path, required=True)
    parser.add_argument("--heldout-v13", type=Path, required=True)
    parser.add_argument("--candidate-ledger", type=Path, default=Path("stage2/openevolve/candidate_ledger.jsonl"))
    parser.add_argument("--scale-gpt5mini", type=Path, default=Path("results/stage2_openevolve/scale/gpt5mini_stage1_iter80_20260430"))
    parser.add_argument("--scale-gpt54", type=Path, default=Path("results/stage2_openevolve/scale/gpt54_stage1_iter80_20260429_224042"))
    parser.add_argument("--scale-sonnet46", type=Path, default=Path("results/stage2_openevolve/scale/claude_sonnet46_stage1_iter30_20260430"))
    parser.add_argument("--figures-dir", type=Path, default=Path("report/figures"))
    parser.add_argument("--tables-dir", type=Path, default=Path("report/tables"))
    args = parser.parse_args()

    args.figures_dir.mkdir(parents=True, exist_ok=True)
    args.tables_dir.mkdir(parents=True, exist_ok=True)
    rows = metric_table(args.train_v12, args.train_v13, args.heldout_v12, args.heldout_v13)
    write_markdown_table(rows, args.tables_dir / "stage2_final_metrics.md")
    instruction_rows = [
        summarize_instruction_check(args.train_v13, "MoP-V1.3", "13-trace training-split validation"),
        summarize_instruction_check(args.heldout_v13, "MoP-V1.3", "7-trace heldout"),
    ]
    write_instruction_check_table(instruction_rows, args.tables_dir / "stage2_instruction_cycle_check.md")
    scale_rows = scale_model_rows(
        args.candidate_ledger,
        [
            ("GPT-5 mini", args.scale_gpt5mini),
            ("GPT-5.4", args.scale_gpt54),
            ("Sonnet 4.6", args.scale_sonnet46),
        ],
    )
    write_scale_model_table(scale_rows, args.tables_dir / "stage2_scale_model_summary.md")
    write_policy_summary_table(policy_summary_rows(scale_rows, args.candidate_ledger), args.tables_dir / "stage2_policy_summary.md")
    plot_pre_post(rows, args.figures_dir / "stage2_pre_post_geomean.png")
    plot_v1_v2_trace_delta(
        args.train_v12,
        args.train_v13,
        args.heldout_v12,
        args.heldout_v13,
        args.figures_dir / "stage2_v1_v2_trace_delta.png",
    )
    plot_heldout_trace_profile(args.heldout_v12, args.heldout_v13, args.figures_dir / "stage2_heldout_trace_profile.png")
    plot_routing_behavior_stats(
        args.train_v12,
        args.train_v13,
        args.heldout_v12,
        args.heldout_v13,
        args.figures_dir / "stage2_routing_behavior_stats.png",
    )
    active_screen = required_ledger_record_for_hash(args.candidate_ledger, "a52ed8a4151ad6cc", "stage1")
    active_confirm = required_ledger_record_for_hash(args.candidate_ledger, "a52ed8a4151ad6cc", "stage2")
    active_screen_nopref = float(active_screen["metrics"]["gm_vs_nopref"])
    active_screen_cap = active_screen_nopref / float(active_screen["metrics"]["gm_vs_pair_best"])
    active_confirm_nopref = float(active_confirm["metrics"]["gm_vs_nopref"])
    active_confirm_cap = active_confirm_nopref / float(active_confirm["metrics"]["gm_vs_pair_best"])
    plot_scale_model_comparison(
        scale_rows,
        args.figures_dir / "stage2_scale_model_comparison.png",
        [
            ("GPT-5 mini", args.scale_gpt5mini),
            ("GPT-5.4", args.scale_gpt54),
            ("Sonnet 4.6", args.scale_sonnet46),
        ],
        active_screen_nopref,
        active_screen_cap,
        active_confirm_nopref,
        active_confirm_cap,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
