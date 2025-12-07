#!/usr/bin/env python3
"""
Generate ops_coverage.json summarizing structural/runtime evidence per operation.

Structural evidence is implied by presence in ops.json (harvested vocab).
Runtime evidence is set when an operation appears in expected matrices from runtime-checks,
runtime-adversarial, or golden-triple profiles.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Set

REPO_ROOT = Path(__file__).resolve().parents[4]
OPS_JSON = REPO_ROOT / "book" / "graph" / "mappings" / "vocab" / "ops.json"
OUT_JSON = REPO_ROOT / "book" / "graph" / "mappings" / "vocab" / "ops_coverage.json"

RUNTIME_MATRICES = [
    REPO_ROOT / "book" / "experiments" / "runtime-checks" / "out" / "expected_matrix.json",
    REPO_ROOT / "book" / "experiments" / "runtime-adversarial" / "out" / "expected_matrix.json",
    REPO_ROOT / "book" / "profiles" / "golden-triple" / "expected_matrix.json",
]


def load_runtime_ops() -> Set[str]:
    ops: Set[str] = set()
    for path in RUNTIME_MATRICES:
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        for prof in (data.get("profiles") or {}).values():
            for probe in prof.get("probes") or []:
                op = probe.get("operation")
                if op:
                    ops.add(op)
    return ops


def main() -> int:
    assert OPS_JSON.exists(), f"missing ops.json at {OPS_JSON}"
    vocab = json.loads(OPS_JSON.read_text())
    ops_list = vocab.get("ops") or []
    runtime_ops = load_runtime_ops()

    coverage: Dict[str, Dict[str, object]] = {}
    for entry in ops_list:
        name = entry["name"]
        op_id = entry["id"]
        coverage[name] = {
            "id": op_id,
            "structural_evidence": True,
            "runtime_evidence": name in runtime_ops,
            "notes": "",
        }

    OUT_JSON.write_text(json.dumps(coverage, indent=2))
    print(f"[+] wrote {OUT_JSON} (runtime_ops={sorted(runtime_ops)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
