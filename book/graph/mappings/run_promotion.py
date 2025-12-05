"""
Thin promotion helper: run validation for selected tags/ids then call mapping generators.

Usage example (runtime + system profiles + CARTON coverage + indices):
    python -m book.graph.mappings.run_promotion --generators runtime,system-profiles,carton-coverage,carton-indices
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

GENERATOR_CMDS = {
    "runtime": [
        [sys.executable, str(ROOT / "graph" / "mappings" / "runtime" / "generate_runtime_signatures.py")],
    ],
    "system-profiles": [
        [sys.executable, str(ROOT / "graph" / "mappings" / "system_profiles" / "generate_digests_from_ir.py")],
    ],
    "carton-coverage": [
        [sys.executable, str(ROOT / "graph" / "mappings" / "carton" / "generate_coverage_from_carton.py")],
    ],
    "carton-indices": [
        [sys.executable, str(ROOT / "graph" / "mappings" / "carton" / "generate_operation_index.py")],
        [sys.executable, str(ROOT / "graph" / "mappings" / "carton" / "generate_profile_layer_index.py")],
    ],
}


def run_validation(tags):
    cmd = [sys.executable, "-m", "book.graph.concepts.validation"]
    for tag in tags:
        cmd.extend(["--tag", tag])
    subprocess.check_call(cmd, cwd=ROOT.parent)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--generators",
        default="runtime,system-profiles,carton-coverage,carton-indices",
        help="comma-separated generators to run (runtime,system-profiles,carton-coverage,carton-indices)",
    )
    args = ap.parse_args()
    gens = [g.strip() for g in args.generators.split(",") if g.strip()]
    tags = {"smoke"}
    if "system-profiles" in gens:
        tags.add("system-profiles")
    if "carton-coverage" in gens or "carton-indices" in gens:
        tags.add("system-profiles")

    run_validation(sorted(tags))

    for gen in gens:
        cmds = GENERATOR_CMDS.get(gen)
        if not cmds:
            raise SystemExit(f"unknown generator: {gen}")
        for cmd in cmds:
            subprocess.check_call(cmd, cwd=ROOT.parent)


if __name__ == "__main__":
    main()
