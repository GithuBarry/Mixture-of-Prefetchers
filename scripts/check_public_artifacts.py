#!/usr/bin/env python3
"""Lightweight checks for public report, deck, and artifact hygiene."""

from __future__ import annotations

import re
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_TEXT = [
    ROOT / "README.md",
    ROOT / "docs" / "outsider_guide.md",
    ROOT / "report" / "stage2_final_report.md",
    ROOT / "report" / "writing_logistics.md",
    ROOT / "slides" / "mop_stage2_final" / "src" / "deck.mjs",
]
PUBLIC_TABLES = [
    ROOT / "report" / "tables" / "stage2_final_metrics.md",
    ROOT / "report" / "tables" / "stage2_scale_model_summary.md",
    ROOT / "report" / "tables" / "stage2_instruction_cycle_check.md",
    ROOT / "report" / "tables" / "stage2_policy_summary.md",
]
LONG_DECIMAL = re.compile(r"(?<![\w.])-?\d+\.\d{4,}(?![\w.])")
SECRET_PATTERN = re.compile(r"sk-[A-Za-z0-9_-]{20,}")


def fail(message: str) -> None:
    raise SystemExit(message)


def check_exists(paths: list[Path]) -> None:
    missing = [str(path.relative_to(ROOT)) for path in paths if not path.exists()]
    if missing:
        fail("Missing public artifacts:\n" + "\n".join(missing))


def check_public_number_format(paths: list[Path]) -> None:
    allowed = {
        "stage2_final_report.md": {"[1.0, 0.55, 1.0]"},
        "README.md": {"[1.0, 0.55, 1.0]"},
    }
    problems: list[str] = []
    for path in paths:
        text = path.read_text()
        for line_no, line in enumerate(text.splitlines(), 1):
            if line.strip() in allowed.get(path.name, set()):
                continue
            match = LONG_DECIMAL.search(line)
            if match:
                problems.append(f"{path.relative_to(ROOT)}:{line_no}: {match.group(0)}")
    if problems:
        fail("Public Markdown and deck text should display at most three decimals:\n" + "\n".join(problems[:50]))


def check_public_naming() -> None:
    problems: list[str] = []
    for path in PUBLIC_TEXT:
        if path.name == "writing_logistics.md":
            continue
        text = path.read_text()
        if "MoP-V1.2" in text or "MoP-V1.3" in text:
            problems.append(str(path.relative_to(ROOT)))
    if problems:
        fail("Public-facing files should use MoP-V1 and MoP-V2 names:\n" + "\n".join(problems))


def check_markdown_images() -> None:
    report = ROOT / "report" / "stage2_final_report.md"
    text = report.read_text()
    problems: list[str] = []
    for match in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", text):
        target = match.group(1)
        if target.startswith(("http://", "https://")):
            continue
        if not (report.parent / target).exists():
            problems.append(target)
    if problems:
        fail("Broken report image references:\n" + "\n".join(problems))


def check_secret_patterns() -> None:
    problems: list[str] = []
    skip_dirs = {".git", "external", "results", "artifacts", "temp", "__pycache__", ".pytest_cache"}
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [dirname for dirname in dirnames if dirname not in skip_dirs]
        base = Path(dirpath)
        for filename in filenames:
            path = base / filename
            rel = path.relative_to(ROOT)
            try:
                text = path.read_text(errors="ignore")
            except OSError:
                continue
            if SECRET_PATTERN.search(text):
                problems.append(str(rel))
    if problems:
        fail("Potential API key pattern found:\n" + "\n".join(problems))


def main() -> int:
    paths = PUBLIC_TEXT + PUBLIC_TABLES
    check_exists(paths)
    check_public_number_format(paths)
    check_public_naming()
    check_markdown_images()
    check_secret_patterns()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
