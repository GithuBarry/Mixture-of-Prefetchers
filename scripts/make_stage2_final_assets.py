#!/usr/bin/env python3
"""Build final Stage 2 report tables and figures from raw run artifacts."""

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
    "MoP-V1.2": COLORS["orange"],
    "MoP-V1.3": COLORS["pink"],
    "pair-best": COLORS["black"],
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
        beats_weaker += r > weaker
        catastrophic += (r / pair_best) < 0.95
        both_gt_1 += e0 > 1.0 and e1 > 1.0
        closer += abs(pair_best - r) <= abs(r - weaker)
    return {
        "n": float(len(traces)),
        "gm_vs_nopref": geomean(vs_base),
        "gm_vs_pair_best": geomean(vs_pair),
        "gm_vs_weaker": geomean(vs_weaker),
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


def metric_table(
    train_v12: Path,
    train_v13: Path,
    heldout_v12: Path,
    heldout_v13: Path,
) -> list[dict[str, str]]:
    rows = []
    specs = [
        ("train-window", "MoP-V1.2", train_v12, "MoP-V1.2"),
        ("train-window", "MoP-V1.3", train_v13, "MoP-V1.3"),
        ("heldout", "MoP-V1.2", heldout_v12, "MoP-V1.2"),
        ("heldout", "MoP-V1.3", heldout_v13, "MoP-V1.3"),
    ]
    for split, label, path, router in specs:
        metrics = summarize_router(path, router)
        rows.append({
            "split": split,
            "method": label,
            "n": str(int(metrics["n"])),
            "gm_vs_pair_best": f"{metrics['gm_vs_pair_best']:.6f}",
            "gm_vs_nopref": f"{metrics['gm_vs_nopref']:.6f}",
            "gm_vs_weaker": f"{metrics['gm_vs_weaker']:.6f}",
            "beats_weaker": f"{int(metrics['beats_weaker'])}/{int(metrics['n'])}",
            "catastrophic": f"{int(metrics['catastrophic'])}/{int(metrics['n'])}",
            "closer_to_better": f"{int(metrics['closer_to_better'])}/{int(metrics['n'])}",
            "both_routees_gt_1": f"{int(metrics['both_routees_gt_1'])}/{int(metrics['n'])}",
        })
    for split, path in [("train-window", train_v13), ("heldout", heldout_v13)]:
        for experiment in ["MLOP", "SPP+PPF"]:
            metrics = summarize_single(path, experiment)
            rows.append({
                "split": split,
                "method": experiment,
                "n": str(int(metrics["n"])),
                "gm_vs_pair_best": "",
                "gm_vs_nopref": f"{metrics['gm_vs_nopref']:.6f}",
                "gm_vs_weaker": "",
                "beats_weaker": "",
                "catastrophic": "",
                "closer_to_better": "",
                "both_routees_gt_1": "",
            })
    return rows


def write_markdown_table(rows: list[dict[str, str]], path: Path) -> None:
    cols = [
        "split",
        "method",
        "n",
        "gm_vs_pair_best",
        "gm_vs_nopref",
        "gm_vs_weaker",
        "beats_weaker",
        "catastrophic",
        "closer_to_better",
        "both_routees_gt_1",
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


def ledger_record_for_hash(ledger_path: Path, code_hash: str, stage: str) -> dict | None:
    records = [json.loads(line) for line in ledger_path.read_text().splitlines() if line.strip()]
    matches = [r for r in records if r.get("code_hash") == code_hash and r.get("stage") == stage]
    if not matches:
        return None
    return matches[-1]


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
        rows.append({
            "model": model,
            "iterations_seen": str(int(latest["current_iteration"])),
            "best_screen_iter": str(int(best["iteration"])),
            "screen_gm_vs_pair_best": f"{float(metrics['gm_vs_pair_best']):.6f}",
            "screen_gm_vs_nopref": f"{float(metrics['gm_vs_nopref']):.6f}",
            "screen_combined": f"{float(metrics['combined_score']):.6f}",
            "confirmed_10_trace_pair_best": (
                f"{float(confirmed_metrics['gm_vs_pair_best']):.6f}" if confirmed_metrics else ""
            ),
            "confirmed_10_trace_combined": (
                f"{float(confirmed_metrics['combined_score']):.6f}" if confirmed_metrics else ""
            ),
            "result_dir": f"results/stage2_openevolve/stage1/{code_hash}" if code_hash else "",
        })
    return rows


def write_scale_model_table(rows: list[dict[str, str]], path: Path) -> None:
    cols = [
        "model",
        "iterations_seen",
        "best_screen_iter",
        "screen_gm_vs_pair_best",
        "screen_gm_vs_nopref",
        "screen_combined",
        "confirmed_10_trace_pair_best",
        "confirmed_10_trace_combined",
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
    router_rows = [r for r in rows if r["method"].startswith("MoP")]
    splits = ["train-window", "heldout"]
    methods = ["MoP-V1.2", "MoP-V1.3"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), sharey=False)
    metrics = [
        ("gm_vs_pair_best", "Geomean vs pair-best single"),
        ("gm_vs_nopref", "Geomean vs no-prefetch"),
    ]
    width = 0.34
    for ax, (metric, title) in zip(axes, metrics, strict=True):
        for i, split in enumerate(splits):
            for j, method in enumerate(methods):
                row = next(r for r in router_rows if r["split"] == split and r["method"] == method)
                value = float(row[metric])
                x = i + (j - 0.5) * width
                ax.bar(
                    x,
                    value,
                    width=width,
                    color=METHOD_COLOR[method],
                    alpha=0.65 if method == "MoP-V1.2" else 1.0,
                    edgecolor=COLORS["black"],
                    linewidth=0.8,
                    label=method if i == 0 else None,
                )
                ax.text(x, value + 0.006, f"{value:.3f}", ha="center", va="bottom", fontsize=8)
        ax.axhline(1.0, color=COLORS["black"], linestyle=":", linewidth=1.0)
        ax.set_xticks(range(len(splits)))
        ax.set_xticklabels(["train\nwindow", "heldout"])
        ax.set_title(title)
        ax.grid(True, axis="y", linestyle=":")
    axes[0].set_ylim(0.93, 1.02)
    axes[1].set_ylim(0.96, 1.10)
    axes[0].legend(frameon=False, loc="lower right")
    fig.suptitle("OpenEvolve closes the train gap, heldout only clears no-prefetch")
    fig.text(
        0.02,
        0.01,
        "Pair-best is the primary bar; no-prefetch is secondary. The same two routers are compared on train-window and heldout runs.",
        ha="left",
        va="bottom",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.06, 1, 0.94))
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
            label=method,
        )
    pair = [
        max(
            float(traces[t]["MLOP"]["speedup_vs_baseline"]),
            float(traces[t]["SPP+PPF"]["speedup_vs_baseline"]),
        )
        for t in ordered
    ]
    ax.scatter(pair, y, marker="|", s=260, color=COLORS["black"], linewidth=2.0, label="pair-best")
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
    ax.set_xlabel("IPC speedup vs no-prefetch")
    ax.set_title("Heldout trace profile: expert complementarity and router placement")
    ax.grid(True, axis="x", linestyle=":")
    ax.legend(frameon=False, ncols=4, loc="lower right")
    fig.text(
        0.02,
        0.01,
        "Each row shows both routee experts, the post-OpenEvolve router, and the per-trace pair-best single. The grey span shows the local spread among the three measured methods.",
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
    axes[1].legend(frameon=False)
    for ax in axes:
        ax.grid(True, axis="y", linestyle=":")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_scale_model_comparison(rows: list[dict[str, str]], out_path: Path) -> None:
    setup_plot()
    labels = [row["model"] for row in rows]
    screen = [float(row["screen_gm_vs_pair_best"]) for row in rows]
    confirmed = [
        float(row["confirmed_10_trace_pair_best"]) if row["confirmed_10_trace_pair_best"] else float("nan")
        for row in rows
    ]
    active_stage2 = 0.9801372167719825
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    x = list(range(len(labels)))
    axes[0].bar(x, screen, color=COLORS["blue"], edgecolor=COLORS["black"], linewidth=0.8)
    axes[0].axhline(0.9358978060739194, color=COLORS["black"], linestyle=":", linewidth=1.1, label="active seed screen")
    axes[0].set_title("Scaled search improved the cheap screen")
    axes[0].set_ylabel("3-trace geomean vs pair-best")
    axes[0].set_ylim(0.932, 0.942)
    axes[0].legend(frameon=False)
    for xi, value in zip(x, screen, strict=True):
        axes[0].text(xi, value + 0.0003, f"{value:.3f}", ha="center", va="bottom", fontsize=8)
    for xi, value in zip(x, confirmed, strict=True):
        axes[1].bar(
            xi,
            0 if math.isnan(value) else value,
            color=COLORS["purple"],
            edgecolor=COLORS["black"],
            linewidth=0.8,
            alpha=0.25 if math.isnan(value) else 0.9,
        )
        if not math.isnan(value):
            axes[1].text(xi, value + 0.0004, f"{value:.3f}", ha="center", va="bottom", fontsize=8)
    axes[1].axhline(active_stage2, color=COLORS["pink"], linewidth=1.6, label="active seed 10-trace")
    axes[1].set_title("Wider confirmation kept the frozen seed")
    axes[1].set_ylabel("10-trace geomean vs pair-best")
    axes[1].set_ylim(0.976, 0.982)
    axes[1].legend(frameon=False)
    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.grid(True, axis="y", linestyle=":")
    fig.text(
        0.02,
        0.01,
        "Only the strongest scaled-search hit was promoted to 10-trace confirmation. Blank confirmation bars mean the screen result trailed the promoted hit.",
        ha="left",
        va="bottom",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.06, 1, 1))
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
    plot_scale_model_comparison(scale_rows, args.figures_dir / "stage2_scale_model_comparison.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
