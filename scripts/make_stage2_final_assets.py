#!/usr/bin/env python3
"""Build final OpenEvolve report tables and figures from raw run artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


COLORS = {
    "yellow": "#ffb000",
    "orange": "#fe6100",
    "pink": "#dc267f",
    "purple": "#785ef0",
    "blue": "#648fff",
    "black": "#000000",
    "white": "#ffffff",
    "lightgrey": "#d9d9d9",
}

METHOD_COLOR = {
    "MLOP": COLORS["blue"],
    "SPP+PPF": COLORS["purple"],
    "Manual router": COLORS["orange"],
    "OpenEvolve router": COLORS["pink"],
    "MoP-V1.3": COLORS["pink"],
    "oracle": COLORS["black"],
}


def geomean(values: list[float]) -> float:
    assert values
    assert min(values) > 0
    return math.exp(sum(math.log(v) for v in values) / len(values))


def load_summary(path: Path) -> list[dict[str, str]]:
    summary = path / "summary.csv"
    assert summary.exists(), f"Missing {summary}"
    return list(csv.DictReader(summary.open()))


def by_trace(rows: list[dict[str, str]]) -> dict[str, dict[str, dict[str, str]]]:
    out: dict[str, dict[str, dict[str, str]]] = {}
    for row in rows:
        out.setdefault(row["trace"], {})[row["experiment"]] = row
    return out


def summarize_router(result_dir: Path, router: str) -> dict[str, float]:
    rows = load_summary(result_dir)
    traces = by_trace(rows)
    vs_base: list[float] = []
    vs_pair: list[float] = []
    vs_weaker: list[float] = []
    pair_best_vs_base: list[float] = []
    weaker_vs_base: list[float] = []
    beats_weaker = 0
    catastrophic = 0
    both_gt_1 = 0
    closer = 0
    for trace_rows in traces.values():
        r = float(trace_rows[router]["speedup_vs_baseline"])
        e0 = float(trace_rows["MLOP"]["speedup_vs_baseline"])
        e1 = float(trace_rows["SPP+PPF"]["speedup_vs_baseline"])
        pair_best = max(e0, e1)
        weaker = min(e0, e1)
        vs_base.append(r)
        vs_pair.append(r / pair_best)
        vs_weaker.append(r / weaker)
        pair_best_vs_base.append(pair_best)
        weaker_vs_base.append(weaker)
        beats_weaker += r > weaker
        catastrophic += (r / pair_best) < 0.95
        both_gt_1 += e0 > 1.0 and e1 > 1.0
        closer += abs(pair_best - r) <= abs(r - weaker)
    return {
        "n": float(len(traces)),
        "gm_vs_nopref": geomean(vs_base),
        "gm_vs_pair_best": geomean(vs_pair),
        "gm_vs_weaker": geomean(vs_weaker),
        "pair_best_vs_nopref": geomean(pair_best_vs_base),
        "weaker_vs_nopref": geomean(weaker_vs_base),
        "beats_weaker": float(beats_weaker),
        "catastrophic": float(catastrophic),
        "both_routees_gt_1": float(both_gt_1),
        "closer_to_better": float(closer),
    }


def summarize_single(result_dir: Path, experiment: str) -> dict[str, float]:
    rows = load_summary(result_dir)
    vals = [float(row["speedup_vs_baseline"]) for row in rows if row["experiment"] == experiment]
    assert vals
    return {"n": float(len(vals)), "gm_vs_nopref": geomean(vals)}


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
        "surface": label,
        "n": str(len(traces)),
        "ipc_speedup_vs_prefetcher_off": f"{geomean(ipc_speedups):.6f}",
        "instruction_count_ratio_vs_prefetcher_off": f"{geomean(instr_ratios):.9f}",
        "cycle_count_ratio_vs_prefetcher_off": f"{geomean(cycle_ratios):.6f}",
        "max_instruction_ratio_delta": f"{max_instr_delta:.9f}",
    }


def metric_table(
    train_v12: Path,
    train_v13: Path,
    heldout_v12: Path,
    heldout_v13: Path,
) -> list[dict[str, str]]:
    rows = []
    specs = [
        ("training validation", "Manual router", train_v12, "MoP-V1.2"),
        ("training validation", "OpenEvolve router", train_v13, "MoP-V1.3"),
        ("heldout", "Manual router", heldout_v12, "MoP-V1.2"),
        ("heldout", "OpenEvolve router", heldout_v13, "MoP-V1.3"),
    ]
    for split, label, path, router in specs:
        metrics = summarize_router(path, router)
        rows.append({
            "split": split,
            "method": label,
            "n": str(int(metrics["n"])),
            "speedup_vs_prefetcher_off": f"{metrics['gm_vs_nopref']:.6f}",
            "oracle_best_prefetcher_cap": f"{metrics['pair_best_vs_nopref']:.6f}",
            "ratio_to_oracle_best": f"{metrics['gm_vs_pair_best']:.6f}",
            "ratio_to_worse_prefetcher": f"{metrics['gm_vs_weaker']:.6f}",
            "beats_worse_prefetcher": f"{int(metrics['beats_weaker'])}/{int(metrics['n'])}",
            "below_0.95x_oracle_best": f"{int(metrics['catastrophic'])}/{int(metrics['n'])}",
            "closer_to_oracle_best": f"{int(metrics['closer_to_better'])}/{int(metrics['n'])}",
            "both_prefetchers_beat_disabled": f"{int(metrics['both_routees_gt_1'])}/{int(metrics['n'])}",
        })
    for split, path in [("training validation", train_v13), ("heldout", heldout_v13)]:
        for experiment in ["MLOP", "SPP+PPF"]:
            metrics = summarize_single(path, experiment)
            rows.append({
                "split": split,
                "method": experiment,
                "n": str(int(metrics["n"])),
                "speedup_vs_prefetcher_off": f"{metrics['gm_vs_nopref']:.6f}",
                "oracle_best_prefetcher_cap": "",
                "ratio_to_oracle_best": "",
                "ratio_to_worse_prefetcher": "",
                "beats_worse_prefetcher": "",
                "below_0.95x_oracle_best": "",
                "closer_to_oracle_best": "",
                "both_prefetchers_beat_disabled": "",
            })
    return rows


def write_markdown_table(rows: list[dict[str, str]], path: Path) -> None:
    cols = [
        "split",
        "method",
        "n",
        "speedup_vs_prefetcher_off",
        "oracle_best_prefetcher_cap",
        "ratio_to_oracle_best",
        "ratio_to_worse_prefetcher",
        "beats_worse_prefetcher",
        "below_0.95x_oracle_best",
        "closer_to_oracle_best",
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
        "surface",
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
        screen_nopref = float(metrics["gm_vs_nopref"])
        screen_pair_best_ratio = float(metrics["gm_vs_pair_best"])
        confirmed_nopref = float(confirmed_metrics["gm_vs_nopref"]) if confirmed_metrics else None
        confirmed_pair_best_ratio = float(confirmed_metrics["gm_vs_pair_best"]) if confirmed_metrics else None
        rows.append({
            "model": model,
            "iterations_seen": str(int(latest["current_iteration"])),
            "best_screen_iter": str(int(best["iteration"])),
            "quick_eval_speedup_vs_prefetcher_off": f"{screen_nopref:.6f}",
            "quick_eval_oracle_cap": f"{screen_nopref / screen_pair_best_ratio:.6f}",
            "quick_eval_ratio_to_oracle_best": f"{screen_pair_best_ratio:.6f}",
            "quick_eval_weighted_score": f"{float(metrics['combined_score']):.6f}",
            "wider_eval_speedup_vs_prefetcher_off": f"{confirmed_nopref:.6f}" if confirmed_nopref else "",
            "wider_eval_oracle_cap": (
                f"{confirmed_nopref / confirmed_pair_best_ratio:.6f}"
                if confirmed_nopref and confirmed_pair_best_ratio
                else ""
            ),
            "wider_eval_ratio_to_oracle_best": f"{confirmed_pair_best_ratio:.6f}" if confirmed_pair_best_ratio else "",
            "wider_eval_weighted_score": f"{float(confirmed_metrics['combined_score']):.6f}" if confirmed_metrics else "",
            "result_dir": f"results/stage2_openevolve/stage1/{code_hash}" if code_hash else "",
        })
    return rows


def write_scale_model_table(rows: list[dict[str, str]], path: Path) -> None:
    cols = [
        "model",
        "iterations_seen",
        "best_screen_iter",
        "quick_eval_speedup_vs_prefetcher_off",
        "quick_eval_oracle_cap",
        "quick_eval_ratio_to_oracle_best",
        "quick_eval_weighted_score",
        "wider_eval_speedup_vs_prefetcher_off",
        "wider_eval_oracle_cap",
        "wider_eval_ratio_to_oracle_best",
        "wider_eval_weighted_score",
        "result_dir",
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


def plot_pre_post(rows: list[dict[str, str]], out_path: Path) -> None:
    setup_plot()
    router_rows = [r for r in rows if r["method"] in {"Manual router", "OpenEvolve router"}]
    splits = ["training validation", "heldout"]
    methods = ["Manual router", "OpenEvolve router"]
    fig, ax = plt.subplots(figsize=(10, 4.8))
    width = 0.34
    cap_label_done = False
    for i, split in enumerate(splits):
        split_rows = [r for r in router_rows if r["split"] == split]
        cap = float(split_rows[0]["oracle_best_prefetcher_cap"])
        ax.scatter(
            [i],
            [cap],
            marker="_",
            s=900,
            color=COLORS["black"],
            linewidth=2.2,
            label="oracle best cap" if not cap_label_done else None,
            zorder=4,
        )
        ax.text(i, cap + 0.006, f"cap {cap:.3f}", ha="center", va="bottom", fontsize=8)
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
                alpha=0.65 if method == "Manual router" else 1.0,
                edgecolor=COLORS["black"],
                linewidth=0.8,
                label=method if i == 0 else None,
            )
            ax.text(x, value + 0.006, f"{value:.3f}", ha="center", va="bottom", fontsize=8)
    ax.axhline(1.0, color=COLORS["black"], linestyle=":", linewidth=1.0, label="prefetcher off")
    ax.set_xticks(range(len(splits)))
    ax.set_xticklabels(["13-trace\ntraining validation", "7-trace\nheldout"])
    ax.set_ylabel("Geomean IPC speedup vs disabled prefetching")
    ax.set_title("Router performance uses disabled prefetching as 1x")
    ax.set_ylim(0.96, 1.12)
    ax.grid(True, axis="y", linestyle=":")
    ax.legend(frameon=False, loc="upper right", ncols=2)
    fig.text(
        0.02,
        0.01,
        "Black caps show max(MLOP, SPP+PPF) per trace before geomean. Bars show the manual router and the OpenEvolve-selected router on the same baseline.",
        ha="left",
        va="bottom",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_heldout_trace_profile(heldout_v13: Path, out_path: Path) -> None:
    setup_plot()
    traces = by_trace(load_summary(heldout_v13))
    ordered = sorted(traces)
    y = list(range(len(ordered)))
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    for method, marker, size in [
        ("MLOP", "o", 42),
        ("SPP+PPF", "s", 42),
        ("MoP-V1.3", "D", 48),
    ]:
        xs = [float(traces[t][method]["speedup_vs_baseline"]) for t in ordered]
        ax.scatter(
            xs,
            y,
            marker=marker,
            s=size,
            color=METHOD_COLOR[method],
            edgecolor=COLORS["black"],
            linewidth=0.5,
            label="OpenEvolve router" if method == "MoP-V1.3" else method,
        )
    pair = [
        max(
            float(traces[t]["MLOP"]["speedup_vs_baseline"]),
            float(traces[t]["SPP+PPF"]["speedup_vs_baseline"]),
        )
        for t in ordered
    ]
    ax.scatter(pair, y, marker="|", s=260, color=COLORS["black"], linewidth=2.0, label="oracle best cap")
    for yi, t in enumerate(ordered):
        values = [
            float(traces[t]["MLOP"]["speedup_vs_baseline"]),
            float(traces[t]["SPP+PPF"]["speedup_vs_baseline"]),
            float(traces[t]["MoP-V1.3"]["speedup_vs_baseline"]),
        ]
        ax.hlines(yi, min(values), max(values), color=COLORS["lightgrey"], linewidth=1.0, zorder=0)
    ax.axvline(1.0, color=COLORS["black"], linestyle=":", linewidth=1.0)
    ax.set_yticks(y)
    ax.set_yticklabels([t.replace(".length_250M", "")[:46] for t in ordered])
    ax.set_xlabel("IPC speedup vs disabled prefetching")
    ax.set_title("Heldout trace profile: expert complementarity and router placement")
    ax.grid(True, axis="x", linestyle=":")
    ax.legend(frameon=False, ncols=4, loc="lower right")
    fig.text(
        0.02,
        0.01,
        "Each row shows both constituent prefetchers, the OpenEvolve-selected router, and the per-trace oracle best cap. The grey span shows the local spread among the measured methods.",
        ha="left",
        va="bottom",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_model_comparison(ledger_path: Path, out_path: Path) -> None:
    setup_plot()
    records = [json.loads(line) for line in ledger_path.read_text().splitlines() if line.strip()]
    active = max(float(record["best_metrics"]["combined_score"]) for record in records)
    labels = []
    scores = []
    valid_counts = []
    invalid_counts = []
    for record in records:
        model = record["model"].replace("claude-haiku-4-5-20251001-v1:0", "Claude\nHaiku 4.5")
        model = model.replace("gpt-5.4-mini", "GPT-5.4\nmini")
        model = model.replace("gpt-5.4-nano", "GPT-5.4\nnano")
        model = model.replace("gpt-5-mini", "GPT-5\nmini")
        if record["config"].endswith("config_modelcmp_gpt54mini.yaml"):
            model = "GPT-5.4\nmini verbose"
        labels.append(model)
        candidate = record.get("best_generated_nonseed")
        scores.append(float(candidate["metrics"]["combined_score"]) if candidate else float("nan"))
        valid_counts.append(int(record["generated_valid_new_candidates"]))
        invalid_counts.append(int(record["generated_invalid_candidates"]) + int(record["gateway_filter_errors"]))
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    x = list(range(len(labels)))
    for xi, score in zip(x, scores, strict=True):
        axes[0].bar(
            xi,
            0 if math.isnan(score) else score,
            color=COLORS["blue"],
            edgecolor=COLORS["black"],
            linewidth=0.8,
            alpha=0.2 if math.isnan(score) else 0.9,
        )
    axes[0].axhline(active, color=COLORS["pink"], linewidth=1.6, label="active seed")
    axes[0].axhline(0.0, color=COLORS["black"], linewidth=0.8)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels)
    axes[0].set_ylabel("Combined score")
    axes[0].set_title("Active seed remains strongest in the model screen")
    axes[0].legend(frameon=False)
    bottom = [0] * len(labels)
    axes[1].bar(x, valid_counts, color=COLORS["purple"], edgecolor=COLORS["black"], linewidth=0.8, label="valid new")
    bottom = valid_counts
    axes[1].bar(
        x,
        invalid_counts,
        bottom=bottom,
        color=COLORS["white"],
        edgecolor=COLORS["black"],
        hatch="//",
        linewidth=0.8,
        label="invalid/filter",
    )
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels)
    axes[1].set_ylabel("Candidate count")
    axes[1].set_title("Model quality was mostly about valid candidates")
    axes[1].legend(frameon=False, loc="lower right")
    for ax in axes:
        ax.grid(True, axis="y", linestyle=":")
    fig.tight_layout()
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
    model_colors = {
        "GPT-5 mini": COLORS["blue"],
        "GPT-5.4": COLORS["orange"],
        "Sonnet 4.6": COLORS["purple"],
    }
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(12.5, 5.1),
        width_ratios=[3.2, 1.0],
        sharey=True,
    )
    ax = axes[0]
    for label, run_dir in scale_runs:
        candidates = checkpoint_candidates(run_dir)
        xs = [int(candidate["iteration_found"]) for candidate in candidates]
        ys = [float(candidate["metrics"]["gm_vs_nopref"]) for candidate in candidates]
        ax.scatter(
            xs,
            ys,
            s=24,
            color=model_colors[label],
            alpha=0.22,
            edgecolor="none",
            label=f"{label} candidates",
        )
        best_points: list[tuple[int, float]] = []
        best_score = -float("inf")
        best_speedup = float("nan")
        for candidate in candidates:
            score = float(candidate["metrics"]["combined_score"])
            if score >= best_score:
                best_score = score
                best_speedup = float(candidate["metrics"]["gm_vs_nopref"])
            best_points.append((int(candidate["iteration_found"]), best_speedup))
        if best_points:
            ax.step(
                [point[0] for point in best_points],
                [point[1] for point in best_points],
                where="post",
                color=model_colors[label],
                linewidth=2.2,
                label=f"{label} best-so-far",
            )
    ax.axhline(1.0, color=COLORS["black"], linestyle=":", linewidth=1.0, label="prefetcher off")
    ax.axhline(active_screen_cap, color=COLORS["black"], linewidth=1.5, label="3-trace oracle cap")
    ax.axhline(active_screen_nopref, color=COLORS["pink"], linewidth=1.8, label="selected policy quick eval")
    ax.set_xlabel("OpenEvolve iteration")
    ax.set_ylabel("3-trace geomean IPC speedup vs disabled prefetching")
    ax.set_title("OpenEvolve search trajectory by model")
    ax.set_ylim(1.00, 1.112)
    ax.grid(True, axis="y", linestyle=":")
    labels = [row["model"] for row in rows]
    quick = [float(row["quick_eval_speedup_vs_prefetcher_off"]) for row in rows]
    wider = [
        float(row["wider_eval_speedup_vs_prefetcher_off"]) if row["wider_eval_speedup_vs_prefetcher_off"] else float("nan")
        for row in rows
    ]
    x = list(range(len(labels)))
    axes[1].scatter(x, quick, marker="o", s=54, color=[model_colors[label] for label in labels], label="3-trace quick eval")
    for xi, value, label in zip(x, wider, labels, strict=True):
        if math.isnan(value):
            axes[1].scatter(xi, 1.001, marker="x", s=60, color=model_colors[label], linewidth=2.0)
            axes[1].text(xi, 1.006, "quick\nonly", ha="center", va="bottom", fontsize=8)
        else:
            axes[1].scatter(xi, value, marker="^", s=64, color=model_colors[label])
    axes[1].axhline(1.0, color=COLORS["black"], linestyle=":", linewidth=1.0)
    axes[1].axhline(active_confirm_cap, color=COLORS["black"], linewidth=1.5)
    axes[1].axhline(active_confirm_nopref, color=COLORS["pink"], linewidth=1.8)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(["GPT-5\nmini", "GPT-5.4", "Sonnet\n4.6"])
    axes[1].set_title("Wider validation")
    axes[1].grid(True, axis="y", linestyle=":")
    handles, legend_labels = ax.get_legend_handles_labels()
    fig.legend(
        handles,
        legend_labels,
        frameon=False,
        ncols=4,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.065),
    )
    fig.text(
        0.02,
        0.01,
        f"Faint points are valid generated candidates. Lines track best-so-far by weighted score. Triangles show 10-trace validation. The selected policy reached {active_confirm_nopref:.3f}x vs disabled prefetching.",
        ha="left",
        va="bottom",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.16, 1, 1))
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-v12", type=Path, default=Path("results/stage2_openevolve/comparators/stage3_v12_current_20260429"))
    parser.add_argument("--train-v13", type=Path, default=Path("results/stage2_openevolve/stage3/a52ed8a4151ad6cc"))
    parser.add_argument("--heldout-v12", type=Path, required=True)
    parser.add_argument("--heldout-v13", type=Path, required=True)
    parser.add_argument("--model-ledger", type=Path, default=Path("stage2/openevolve/model_comparison_ledger.jsonl"))
    parser.add_argument("--candidate-ledger", type=Path, default=Path("stage2/openevolve/candidate_ledger.jsonl"))
    parser.add_argument("--scale-gpt5mini", type=Path, default=Path("results/stage2_openevolve/scale/gpt5mini_stage1_iter80_20260430"))
    parser.add_argument("--scale-gpt54", type=Path, default=Path("results/stage2_openevolve/scale/gpt54_stage1_iter30_20260430"))
    parser.add_argument("--scale-sonnet46", type=Path, default=Path("results/stage2_openevolve/scale/claude_sonnet46_stage1_iter30_20260430"))
    parser.add_argument("--figures-dir", type=Path, default=Path("report/figures"))
    parser.add_argument("--tables-dir", type=Path, default=Path("report/tables"))
    args = parser.parse_args()

    args.figures_dir.mkdir(parents=True, exist_ok=True)
    args.tables_dir.mkdir(parents=True, exist_ok=True)
    rows = metric_table(args.train_v12, args.train_v13, args.heldout_v12, args.heldout_v13)
    write_markdown_table(rows, args.tables_dir / "stage2_final_metrics.md")
    instruction_rows = [
        summarize_instruction_check(args.train_v13, "MoP-V1.3", "13-trace training validation"),
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
    plot_pre_post(rows, args.figures_dir / "stage2_pre_post_geomean.png")
    plot_heldout_trace_profile(args.heldout_v13, args.figures_dir / "stage2_heldout_trace_profile.png")
    plot_model_comparison(args.model_ledger, args.figures_dir / "stage2_model_comparison.png")
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
