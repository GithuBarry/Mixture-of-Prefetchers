#!/usr/bin/env python3
"""Copy the final public MoP artifacts into one clean submission folder."""

from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deliverables" / "MoP-Final"
FIGURES = [
    "stage2_pre_post_geomean.png",
    "stage2_v1_v2_trace_delta.png",
    "stage2_heldout_trace_profile.png",
    "stage2_routing_behavior_stats.png",
    "stage2_scale_model_comparison.png",
]
TABLES = [
    "stage2_final_metrics.md",
    "stage2_instruction_cycle_check.md",
    "stage2_policy_summary.md",
    "stage2_scale_model_summary.md",
]


def copy_file(src: Path, dst: Path) -> None:
    assert src.exists(), f"Missing {src}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def write_readme() -> None:
    text = """# MoP-Final Deliverables

This folder collects the clean public artifacts for the Mixture-of-Prefetchers project.

## Files

- `MoP-Final-report.md`: class-report writeup.
- `MoP-Final-poster.pdf`: portrait poster.
- `MoP-Final-slides.pptx`: slide deck.
- `figures/`: report figures with disabled prefetching as `1.000x`.
- `tables/`: report tables and policy summary.
- `writing_logistics.md`: repo paths, raw-code-name mapping, and rebuild notes.

The source files remain in their normal repo locations so scripts and links keep working.
"""
    (OUT / "README.md").write_text(text)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    copy_file(ROOT / "report" / "stage2_final_report.md", OUT / "MoP-Final-report.md")
    copy_file(ROOT / "output" / "pdf" / "mop_openevolve_poster.pdf", OUT / "MoP-Final-poster.pdf")
    copy_file(ROOT / "slides" / "mop_stage2_final" / "output" / "output.pptx", OUT / "MoP-Final-slides.pptx")
    copy_file(ROOT / "report" / "writing_logistics.md", OUT / "writing_logistics.md")
    for figure in FIGURES:
        copy_file(ROOT / "report" / "figures" / figure, OUT / "figures" / figure)
    for table in TABLES:
        copy_file(ROOT / "report" / "tables" / table, OUT / "tables" / table)
    write_readme()
    print(f"Wrote clean deliverables to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
