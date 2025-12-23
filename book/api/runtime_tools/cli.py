#!/usr/bin/env python3
"""
Unified CLI for runtime tools.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from book.api import path_utils
from book.api.runtime_tools.core import normalize
from book.api.runtime_tools.harness import runner as harness_runner
from book.api.runtime_tools.mapping import story as runtime_story
from book.api.runtime_tools import workflow


REPO_ROOT = path_utils.find_repo_root(Path(__file__))
BOOK_ROOT = REPO_ROOT / "book"


def _default_matrix() -> Path:
    return BOOK_ROOT / "experiments" / "runtime-checks" / "out" / "expected_matrix.json"


def _default_runtime_results() -> Path:
    return BOOK_ROOT / "experiments" / "runtime-checks" / "out" / "runtime_results.json"


def run_command(args: argparse.Namespace) -> int:
    out_path = harness_runner.run_matrix(args.matrix, out_dir=args.out)
    print(f"[+] wrote {out_path}")
    return 0


def normalize_command(args: argparse.Namespace) -> int:
    out_path = normalize.write_matrix_observations(
        args.matrix,
        args.runtime_results,
        args.out,
        world_id=args.world_id,
    )
    print(f"[+] wrote {out_path}")
    return 0


def cut_command(args: argparse.Namespace) -> int:
    cut = workflow.build_cut(
        args.matrix,
        args.runtime_results,
        args.out,
        world_id=args.world_id,
    )
    print(f"[+] wrote {cut.manifest}")
    return 0


def story_command(args: argparse.Namespace) -> int:
    story_doc = runtime_story.build_story(args.ops, args.scenarios, vocab_path=args.vocab, world_id=args.world_id)
    out_path = runtime_story.write_story(story_doc, args.out)
    print(f"[+] wrote {out_path}")
    return 0


def golden_command(args: argparse.Namespace) -> int:
    artifacts = workflow.generate_golden_artifacts(
        matrix_path=args.matrix,
        runtime_results_path=args.runtime_results,
        baseline_ref=args.baseline,
        out_root=args.out,
    )
    print(f"[+] wrote {artifacts.decode_summary}")
    print(f"[+] wrote {artifacts.expectations}")
    print(f"[+] wrote {artifacts.traces}")
    return 0


def promote_command(args: argparse.Namespace) -> int:
    cut = workflow.promote_cut(args.staging, args.out)
    print(f"[+] wrote {cut.manifest}")
    return 0


def mismatch_command(args: argparse.Namespace) -> int:
    matrix_doc = json.loads(Path(args.matrix).read_text())
    runtime_doc = json.loads(Path(args.runtime_results).read_text())
    world_id = args.world_id or matrix_doc.get("world_id") or runtime_doc.get("world_id")
    if not world_id:
        raise SystemExit("world_id missing; pass --world-id")
    summary = workflow.classify_mismatches(matrix_doc, runtime_doc, world_id)
    out_path = Path(args.out)
    out_path.write_text(json.dumps(summary, indent=2))
    print(f"[+] wrote {out_path}")
    return 0


def run_all_command(args: argparse.Namespace) -> int:
    run = workflow.run_from_matrix(
        args.matrix,
        args.out,
        world_id=args.world_id,
    )
    print(f"[+] wrote {run.runtime_results}")
    print(f"[+] wrote {run.cut.manifest}")
    if run.mismatch_summary:
        print(f"[+] wrote {run.mismatch_summary}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Runtime tools (run, normalize, cut, story, promote).")
    sub = ap.add_subparsers(dest="command", required=True)

    ap_run = sub.add_parser("run", help="Run runtime probes for an expected matrix (writes runtime_results.json).")
    ap_run.add_argument("--matrix", type=Path, default=_default_matrix(), help="Path to expected_matrix.json")
    ap_run.add_argument("--out", type=Path, default=BOOK_ROOT / "profiles" / "golden-triple", help="Output directory")
    ap_run.set_defaults(func=run_command)

    ap_norm = sub.add_parser("normalize", help="Normalize expected_matrix + runtime_results into observations.")
    ap_norm.add_argument("--matrix", type=Path, default=_default_matrix(), help="Path to expected_matrix.json")
    ap_norm.add_argument("--runtime-results", type=Path, default=_default_runtime_results(), help="Path to runtime_results.json")
    ap_norm.add_argument("--out", type=Path, required=True, help="Output path for observations JSON")
    ap_norm.add_argument("--world-id", type=str, help="Override world_id")
    ap_norm.set_defaults(func=normalize_command)

    ap_cut = sub.add_parser("cut", help="Generate a runtime cut from expected_matrix + runtime_results.")
    ap_cut.add_argument("--matrix", type=Path, default=_default_matrix(), help="Path to expected_matrix.json")
    ap_cut.add_argument("--runtime-results", type=Path, default=_default_runtime_results(), help="Path to runtime_results.json")
    ap_cut.add_argument("--out", type=Path, required=True, help="Output staging directory for runtime cut")
    ap_cut.add_argument("--world-id", type=str, help="Override world_id")
    ap_cut.set_defaults(func=cut_command)

    ap_story = sub.add_parser("story", help="Build a runtime story from ops + scenarios.")
    ap_story.add_argument("--ops", type=Path, required=True, help="Path to ops.json")
    ap_story.add_argument("--scenarios", type=Path, required=True, help="Path to scenarios.json")
    ap_story.add_argument("--vocab", type=Path, default=BOOK_ROOT / "graph" / "mappings" / "vocab" / "ops.json", help="Path to ops vocab")
    ap_story.add_argument("--out", type=Path, required=True, help="Output path for runtime_story.json")
    ap_story.add_argument("--world-id", type=str, help="Override world_id")
    ap_story.set_defaults(func=story_command)

    ap_golden = sub.add_parser("golden", help="Generate golden decodes/expectations/traces from runtime-checks outputs.")
    ap_golden.add_argument("--matrix", type=Path, default=_default_matrix(), help="Path to expected_matrix.json")
    ap_golden.add_argument("--runtime-results", type=Path, default=_default_runtime_results(), help="Path to runtime_results.json")
    ap_golden.add_argument("--baseline", type=Path, default=BOOK_ROOT / "world" / "sonoma-14.4.1-23E224-arm64" / "world-baseline.json", help="Path to world baseline JSON")
    ap_golden.add_argument("--out", type=Path, default=BOOK_ROOT / "graph" / "mappings" / "runtime", help="Root output directory")
    ap_golden.set_defaults(func=golden_command)

    ap_promote = sub.add_parser("promote", help="Promote a staged runtime cut into runtime_cuts.")
    ap_promote.add_argument("--staging", type=Path, required=True, help="Staging root for runtime cut")
    ap_promote.add_argument("--out", type=Path, default=BOOK_ROOT / "graph" / "mappings" / "runtime_cuts", help="Target root")
    ap_promote.set_defaults(func=promote_command)

    ap_mismatch = sub.add_parser("mismatch", help="Classify mismatches for expected_matrix + runtime_results.")
    ap_mismatch.add_argument("--matrix", type=Path, default=_default_matrix(), help="Path to expected_matrix.json")
    ap_mismatch.add_argument("--runtime-results", type=Path, default=_default_runtime_results(), help="Path to runtime_results.json")
    ap_mismatch.add_argument("--out", type=Path, required=True, help="Output path for mismatch_summary.json")
    ap_mismatch.add_argument("--world-id", type=str, help="Override world_id")
    ap_mismatch.set_defaults(func=mismatch_command)

    ap_all = sub.add_parser("run-all", help="Run matrix, build cut, and emit mismatch summary.")
    ap_all.add_argument("--matrix", type=Path, default=_default_matrix(), help="Path to expected_matrix.json")
    ap_all.add_argument("--out", type=Path, required=True, help="Output directory")
    ap_all.add_argument("--world-id", type=str, help="Override world_id")
    ap_all.set_defaults(func=run_all_command)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
