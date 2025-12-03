#!/usr/bin/env python3
"""
Merge Plan.md and ResearchReport.md into a unified Report.md for each experiment.

The script keeps Plan.md and ResearchReport.md untouched and writes a new
Report.md next to them. It follows a shared section order:

- Title (experiment name)
- Purpose
- Baseline & scope
- Deliverables / expected outcomes
- Plan & execution log (Completed / Planned)
- Evidence & artifacts
- Blockers / risks
- Next steps
- Appendix (for any unmapped sections)
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


def repo_root() -> Path:
    # scripts/ -> experiments/ -> status/ -> repo root
    return Path(__file__).resolve().parents[3]


def normalize_heading(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def parse_markdown_sections(path: Path) -> List[Tuple[Optional[str], int, List[str]]]:
    """Return a list of (heading, level, lines). heading is None for preamble."""
    lines = path.read_text().splitlines()
    sections: List[Tuple[Optional[str], int, List[str]]] = []
    current: Optional[Tuple[Optional[str], int, List[str]]] = None

    heading_re = re.compile(r"^(#{1,6})\s+(.*)")
    for line in lines:
        match = heading_re.match(line)
        if match:
            if current:
                sections.append(current)
            level = len(match.group(1))
            title = match.group(2).strip()
            current = (title, level, [])
        else:
            if current is None:
                current = (None, 0, [])
            current[2].append(line.rstrip())
    if current:
        sections.append(current)
    return sections


def first_matching_section(
    sections: Sequence[Tuple[Optional[str], int, List[str]]],
    keywords: Iterable[str],
    used: set[int],
) -> Optional[str]:
    keyword_list = list(keywords)
    for idx, (title, _level, lines) in enumerate(sections):
        if idx in used or title is None:
            continue
        norm = normalize_heading(title)
        if any(key in norm for key in keyword_list):
            used.add(idx)
            return "\n".join(lines).strip()
    return None


def plan_deliverables_and_sections(plan_path: Path):
    """Extract deliverables lines and Done/Upcoming blocks keyed by section."""
    sections: Dict[str, Dict[str, List[str]]] = {}
    deliverables: List[str] = []
    current_section = "General"
    mode: Optional[str] = None

    heading_re = re.compile(r"^#{2,6}\s+(.*)")
    done_re = re.compile(r"^\s*\*\*Done", re.IGNORECASE)
    upcoming_re = re.compile(r"^\s*\*\*(Upcoming|Planned)", re.IGNORECASE)
    updates_re = re.compile(r"^\s*\*\*Updates", re.IGNORECASE)

    for raw_line in plan_path.read_text().splitlines():
        line = raw_line.rstrip()
        heading_match = heading_re.match(line)
        if heading_match:
            current_section = heading_match.group(1).strip()
            mode = None
            continue

        if re.match(r"^\s*Deliverables:", line, re.IGNORECASE):
            deliverables.append(line.strip())
            continue

        if done_re.match(line):
            mode = "done"
            continue
        if upcoming_re.match(line):
            mode = "upcoming"
            continue
        if updates_re.match(line):
            mode = "updates"
            continue

        if mode:
            if not line.strip():
                continue
            bucket = sections.setdefault(current_section, {"done": [], "upcoming": [], "updates": []})
            bucket[mode].append(line.strip())

    return deliverables, sections


def build_plan_log(sections: Dict[str, Dict[str, List[str]]], current_status: Optional[str]):
    completed: List[str] = []
    planned: List[str] = []

    for sec, buckets in sections.items():
        if buckets.get("done"):
            payload = "\n".join(buckets["done"])
            completed.append(f"**{sec}**\n{payload}")
        if buckets.get("updates"):
            payload = "\n".join(buckets["updates"])
            completed.append(f"**{sec} (updates)**\n{payload}")
        if buckets.get("upcoming"):
            payload = "\n".join(buckets["upcoming"])
            planned.append(f"**{sec}**\n{payload}")

    if current_status:
        completed.insert(0, f"**Current status**\n{current_status.strip()}")

    return completed, planned


def format_bullet_block(label: str, entries: List[str]) -> List[str]:
    lines: List[str] = []
    if label:
        lines.append(label)
    if not entries:
        lines.append("- Not documented.")
        return lines
    for entry in entries:
        entry_lines = entry.splitlines()
        if not entry_lines:
            continue
        first = re.sub(r"^\s*[-*]\s+", "", entry_lines[0]).strip()
        lines.append(f"- {first}")
        for more in entry_lines[1:]:
            lines.append(f"  {more}")
    return lines


def build_report_content(exp_name: str, plan_path: Path, report_path: Path) -> str:
    plan_sections = parse_markdown_sections(plan_path)
    rr_sections = parse_markdown_sections(report_path)
    used_sections: set[int] = set()

    # ResearchReport-driven fields
    report_title = next((title for title, level, _ in rr_sections if level == 1 and title), None)
    purpose = first_matching_section(rr_sections, ["purpose", "goal", "motivation"], used_sections)
    baseline = first_matching_section(rr_sections, ["baseline", "environment", "scope"], used_sections)
    plan_summary = first_matching_section(rr_sections, ["plan", "approach", "steps"], used_sections)
    current_status = first_matching_section(rr_sections, ["current status", "status"], used_sections)
    expected = first_matching_section(rr_sections, ["expected", "outcomes", "deliverables"], used_sections)
    blockers = first_matching_section(rr_sections, ["blocker", "risk", "gap", "open question", "issue"], used_sections)
    evidence = first_matching_section(rr_sections, ["artifact", "evidence", "validation", "dependency", "input"], used_sections)
    next_steps = first_matching_section(rr_sections, ["next step", "future work"], used_sections)

    # Preamble fallback to purpose if empty
    if not purpose and rr_sections and rr_sections[0][0] is None:
        purpose = "\n".join(rr_sections[0][2]).strip()
        used_sections.add(0)

    # Plan-specific extraction
    deliverables_from_plan, plan_section_buckets = plan_deliverables_and_sections(plan_path)
    completed_entries, planned_entries = build_plan_log(plan_section_buckets, current_status)
    if plan_summary:
        planned_entries.insert(0, plan_summary.strip())

    # Fallback if no planned work was captured: include the Plan body.
    if not planned_entries:
        plan_body = "\n".join(
            line for (_title, level, lines) in plan_sections if level >= 2 for line in lines
        ).strip()
        if plan_body:
            planned_entries.append(plan_body)

    # Deliverables merge
    deliverables: List[str] = []
    if expected:
        deliverables.append(expected)
    deliverables.extend(deliverables_from_plan)

    evidence_lines: List[str] = []
    if evidence:
        evidence_lines.append(evidence)

    # Capture any unused RR sections in an appendix
    appendix_chunks: List[str] = []
    for idx, (sec_title, level, lines) in enumerate(rr_sections):
        if idx in used_sections or sec_title is None or level == 1:
            continue
        appendix_chunks.append(f"### {sec_title}\n" + "\n".join(lines).strip())

    name_for_title = report_title or f"{exp_name} – Report"

    content_lines: List[str] = [
        f"# {name_for_title}",
        "",
        "## Purpose",
        purpose.strip() if purpose else "Not documented.",
        "",
        "## Baseline & scope",
        baseline.strip() if baseline else "Not documented.",
        "",
        "## Deliverables / expected outcomes",
        "\n".join(format_bullet_block("", deliverables)) if deliverables else "Not documented.",
        "",
        "## Plan & execution log",
    ]

    content_lines.extend(format_bullet_block("### Completed", completed_entries))
    content_lines.append("")
    content_lines.extend(format_bullet_block("### Planned", planned_entries))
    content_lines.append("")

    content_lines.extend(
        [
            "## Evidence & artifacts",
            "\n".join(evidence_lines).strip() if evidence_lines else "Not documented.",
            "",
            "## Blockers / risks",
            blockers.strip() if blockers else "Not documented.",
            "",
            "## Next steps",
            next_steps.strip() if next_steps else "Not documented.",
        ]
    )

    if appendix_chunks:
        content_lines.append("")
        content_lines.append("## Appendix")
        content_lines.append("\n\n".join(appendix_chunks))

    return "\n".join(content_lines).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(description="Merge Plan.md and ResearchReport.md into Report.md.")
    parser.add_argument(
        "--experiment",
        action="append",
        help="Limit to specific experiment name(s); defaults to all experiments.",
    )
    args = parser.parse_args()

    root = repo_root()
    experiments_dir = root / "book" / "experiments"
    if not experiments_dir.is_dir():
        raise SystemExit(f"Experiments directory not found at {experiments_dir}")

    experiment_names = sorted(p.name for p in experiments_dir.iterdir() if p.is_dir())
    if args.experiment:
        requested = set(args.experiment)
        experiment_names = [name for name in experiment_names if name in requested]

    for name in experiment_names:
        exp_dir = experiments_dir / name
        plan_path = exp_dir / "Plan.md"
        rr_path = exp_dir / "ResearchReport.md"
        if not plan_path.exists() or not rr_path.exists():
            continue
        report_path = exp_dir / "Report.md"
        report_content = build_report_content(name, plan_path, rr_path)
        report_path.write_text(report_content)
        print(f"wrote {report_path.relative_to(root)}")


if __name__ == "__main__":
    main()
