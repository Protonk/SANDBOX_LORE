"""
Public CARTON query API (stable entrypoint for agents and tools).

Implements simple lookups over CARTON mappings (vocab, system profile digests,
runtime signatures, coverage) without touching experiment out/ directly.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[3]
VOCAB_OPS = ROOT / "book/graph/mappings/vocab/ops.json"
SYSTEM_DIGESTS = ROOT / "book/graph/mappings/system_profiles/digests.json"
RUNTIME_SIGS = ROOT / "book/graph/mappings/runtime/runtime_signatures.json"
COVERAGE = ROOT / "book/graph/mappings/carton/operation_coverage.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def profiles_with_operation(op_name: str) -> List[str]:
    coverage = {}
    if COVERAGE.exists():
        coverage = _load_json(COVERAGE).get("coverage") or {}
    if op_name in coverage:
        return coverage[op_name].get("system_profiles", [])
    ops = _load_json(VOCAB_OPS).get("ops") or []
    name_to_id = {entry["name"]: entry["id"] for entry in ops}
    op_id = name_to_id.get(op_name)
    if op_id is None:
        return []
    digests = _load_json(SYSTEM_DIGESTS)
    profiles = []
    for key, val in digests.items():
        if key == "metadata":
            continue
        op_table = val.get("op_table") or []
        if op_id in op_table:
            profiles.append(key)
    return profiles


def profiles_and_signatures_for_operation(op_name: str) -> Dict[str, Any]:
    coverage = {}
    if COVERAGE.exists():
        coverage = _load_json(COVERAGE).get("coverage") or {}
    entry = coverage.get(op_name) or {}
    return {
        "system_profiles": entry.get("system_profiles") or [],
        "runtime_signatures": entry.get("runtime_signatures") or [],
        "counts": entry.get("counts") or {},
    }


def runtime_signature_info(sig_id: str) -> Dict[str, object]:
    sigs = _load_json(RUNTIME_SIGS)
    signatures = sigs.get("signatures") or {}
    meta = sigs.get("profiles_metadata") or {}
    expected = (sigs.get("expected_matrix") or {}).get("profiles") or {}
    return {
        "probes": signatures.get(sig_id),
        "runtime_profile": (meta.get(sig_id) or {}).get("runtime_profile"),
        "expected": expected.get(sig_id),
    }


def ops_with_low_coverage(threshold: int = 0) -> List[Dict[str, object]]:
    if not COVERAGE.exists():
        return []
    coverage = _load_json(COVERAGE).get("coverage") or {}
    low = []
    for name, entry in coverage.items():
        counts = entry.get("counts") or {}
        total = (counts.get("system_profiles", 0) + counts.get("runtime_signatures", 0))
        if total <= threshold:
            low.append({"name": name, "op_id": entry.get("op_id"), "counts": counts})
    low.sort(
        key=lambda rec: (
            rec.get("counts", {}).get("system_profiles", 0)
            + rec.get("counts", {}).get("runtime_signatures", 0),
            rec.get("name"),
        )
    )
    return low


def list_carton_paths() -> Dict[str, str]:
    return {
        "vocab_ops": str(VOCAB_OPS),
        "system_profiles": str(SYSTEM_DIGESTS),
        "runtime_signatures": str(RUNTIME_SIGS),
        "coverage": str(COVERAGE),
    }


__all__ = [
    "list_carton_paths",
    "ops_with_low_coverage",
    "profiles_and_signatures_for_operation",
    "profiles_with_operation",
    "runtime_signature_info",
]
