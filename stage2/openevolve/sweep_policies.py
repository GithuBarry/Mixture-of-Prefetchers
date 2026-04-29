#!/usr/bin/env python3
"""Train-only Stage 2 policy sweep over the frozen MoP knob surface."""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evaluator import (
    RESULTS_ROOT,
    fitness,
    policy_hash,
    repo_relative,
    run_candidate,
    summarize_result,
    validate_policy,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATED_ROOT = RESULTS_ROOT / "generated_candidates"
SWEEP_ROOT = RESULTS_ROOT / "sweeps"

WEIGHT_PRESETS = {
    "seed": [1.0, 0.25, 1.0],
    "no_accuracy": [1.0, 0.0, 1.0],
    "more_accuracy": [1.0, 0.5, 1.0],
    "more_useful": [1.0, 0.25, 2.0],
}


def write_candidate(policy: dict[str, Any]) -> Path:
    payload = json.dumps(policy, sort_keys=True, indent=8)
    compact = json.dumps(policy, sort_keys=True, separators=(",", ":")).encode()
    short = hashlib.sha256(compact).hexdigest()[:16]
    path = GENERATED_ROOT / f"candidate_{short}.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# EVOLVE-BLOCK-START\n"
        "\n"
        "\n"
        "def candidate_policy():\n"
        "    return "
        + payload.replace("\n", "\n    ")
        + "\n"
        "\n"
        "\n"
        "# EVOLVE-BLOCK-END\n"
        "\n"
        "\n"
        "def get_policy_config():\n"
        "    return candidate_policy()\n"
    )
    return path


def focused_policies(preset: str) -> list[dict[str, Any]]:
    policies: list[dict[str, Any]] = []
    if preset == "tight":
        budgets = [4096, 8192, 12288]
        floors = [0, 30]
        v11_shares = [0, 10, 20]
        v12_epochs = [1]
        v12_weights = [WEIGHT_PRESETS["seed"], WEIGHT_PRESETS["no_accuracy"], WEIGHT_PRESETS["more_accuracy"]]
    elif preset == "focused":
        budgets = [4096, 8192, 12288, 16384]
        floors = [0, 30, 45]
        v11_shares = [0, 10, 20]
        v12_epochs = [1, 2]
        v12_weights = list(WEIGHT_PRESETS.values())
    else:
        raise AssertionError(f"Unknown preset: {preset}")
    for router, budget, floor in itertools.product(["MoP-V1.1", "MoP-V1.2"], budgets, floors):
        if router == "MoP-V1.1":
            for share in v11_shares:
                policies.append({
                    "router": router,
                    "mop_total_budget": budget,
                    "mop_one_shot_epochs": 1,
                    "mop_accuracy_floor": floor,
                    "mop_guarded_min_budget_share": share,
                    "mop_score_weights": WEIGHT_PRESETS["seed"],
                })
        else:
            for epochs, weights in itertools.product(v12_epochs, v12_weights):
                policies.append({
                    "router": router,
                    "mop_total_budget": budget,
                    "mop_one_shot_epochs": epochs,
                    "mop_accuracy_floor": floor,
                    "mop_guarded_min_budget_share": 10,
                    "mop_score_weights": weights,
                })
    return [validate_policy(p) for p in policies]


def seed_policy() -> dict[str, Any]:
    return validate_policy({
        "router": "MoP-V1.2",
        "mop_total_budget": 8192,
        "mop_one_shot_epochs": 1,
        "mop_accuracy_floor": 30,
        "mop_guarded_min_budget_share": 10,
        "mop_score_weights": WEIGHT_PRESETS["seed"],
    })


def dedupe(policies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for policy in policies:
        key = json.dumps(policy, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        out.append(policy)
    return out


def evaluate_policy(policy: dict[str, Any], stage: str) -> dict[str, Any]:
    candidate_path = write_candidate(policy)
    code_hash = policy_hash(str(candidate_path), policy)
    result_dir = run_candidate(policy, code_hash, stage)
    metrics = summarize_result(result_dir, policy["router"])
    metrics["combined_score"] = fitness(metrics)
    metrics["stage_passed"] = 1.0
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "code_hash": code_hash,
        "candidate_path": repo_relative(candidate_path),
        "result_dir": repo_relative(result_dir),
        "policy": policy,
        "metrics": metrics,
    }


def evaluate_policy_with_retries(policy: dict[str, Any], stage: str, retries: int) -> dict[str, Any]:
    errors: list[str] = []
    for attempt in range(retries + 1):
        try:
            record = evaluate_policy(policy, stage)
            if errors:
                record["retry_errors"] = errors
            return record
        except Exception as exc:
            errors.append(f"attempt {attempt + 1}: {type(exc).__name__}: {exc}")
            if attempt < retries:
                time.sleep(2)
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "policy": policy,
        "errors": errors,
    }


def is_success(record: dict[str, Any]) -> bool:
    return "metrics" in record


def sort_key(record: dict[str, Any]) -> tuple[float, float, float, float]:
    metrics = record["metrics"]
    return (
        metrics["combined_score"],
        metrics["gm_vs_pair_best"],
        metrics["gm_vs_nopref"],
        metrics["gm_vs_weaker"],
    )


def write_outputs(records: list[dict[str, Any]], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    failures = [record for record in records if not is_success(record)]
    records = [record for record in records if is_success(record)]
    with (out_dir / "records_all.jsonl").open("w") as handle:
        for record in sorted(records + failures, key=lambda r: json.dumps(r.get("policy", {}), sort_keys=True)):
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    if failures:
        with (out_dir / "failures.jsonl").open("w") as handle:
            for record in failures:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
    assert records, "No successful sweep records produced"
    records = sorted(records, key=sort_key, reverse=True)
    with (out_dir / "records.jsonl").open("w") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    metric_keys = sorted(records[0]["metrics"])
    policy_keys = sorted(records[0]["policy"])
    with (out_dir / "summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "rank", "stage", "code_hash", "result_dir", *[f"metric_{k}" for k in metric_keys],
            *[f"policy_{k}" for k in policy_keys],
        ])
        writer.writeheader()
        for rank, record in enumerate(records, start=1):
            row = {
                "rank": rank,
                "stage": record["stage"],
                "code_hash": record["code_hash"],
                "result_dir": record["result_dir"],
            }
            row.update({f"metric_{k}": record["metrics"][k] for k in metric_keys})
            row.update({f"policy_{k}": json.dumps(record["policy"][k]) for k in policy_keys})
            writer.writerow(row)

    top = records[:10]
    lines = [
        "# Stage 2 Policy Sweep",
        "",
        f"- successful records: `{len(records)}`",
        f"- failed records: `{len(failures)}`",
        f"- generated: `{datetime.now(timezone.utc).isoformat()}`",
        "",
        "| rank | router | budget | epochs | floor | share | weights | vs pair-best | vs no-pref | vs weaker | both-on | single | score |",
        "| ---: | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for rank, record in enumerate(top, start=1):
        p = record["policy"]
        m = record["metrics"]
        lines.append(
            f"| {rank} | {p['router']} | {p['mop_total_budget']} | {p.get('mop_one_shot_epochs', '')} | "
            f"{p.get('mop_accuracy_floor', '')} | {p.get('mop_guarded_min_budget_share', '')} | "
            f"`{p.get('mop_score_weights', '')}` | {m['gm_vs_pair_best']:.6f} | "
            f"{m['gm_vs_nopref']:.6f} | {m['gm_vs_weaker']:.6f} | "
            f"{m['both_on_rate']:.3f} | {m['single_action_rate']:.3f} | {m['combined_score']:.6f} |"
        )
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", default="stage1", choices=["stage0", "stage1", "stage2", "stage3", "stage4"])
    parser.add_argument("--workers", type=int, default=max(1, min(8, (os.cpu_count() or 2) // 2)))
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--preset", default="focused", choices=["tight", "focused"])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args()

    policies = dedupe([seed_policy(), *focused_policies(args.preset)])
    if args.limit is not None:
        policies = policies[:args.limit]

    out_dir = args.out_dir or (SWEEP_ROOT / f"{args.stage}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
    records: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(evaluate_policy_with_retries, policy, args.stage, args.retries): policy for policy in policies}
        for future in as_completed(futures):
            record = future.result()
            records.append(record)
            p = record["policy"]
            if is_success(record):
                m = record["metrics"]
                print(
                    f"{len(records)}/{len(policies)} {record['code_hash']} {p['router']} "
                    f"best={m['gm_vs_pair_best']:.6f} nopref={m['gm_vs_nopref']:.6f} "
                    f"weak={m['gm_vs_weaker']:.6f} score={m['combined_score']:.6f}",
                    flush=True,
                )
            else:
                print(f"{len(records)}/{len(policies)} FAILED {p['router']} {record['errors'][-1]}", flush=True)

    assert records, "No sweep records produced"
    write_outputs(records, out_dir)
    print(f"Wrote sweep outputs to {repo_relative(out_dir.resolve())}")
    return 0 if all(is_success(record) for record in records) else 2


if __name__ == "__main__":
    raise SystemExit(main())
