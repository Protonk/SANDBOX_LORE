"""
Simple queries over CARTON mappings (vocab, system_profiles digests, runtime signatures).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[3]
VOCAB_OPS = ROOT / "book/graph/mappings/vocab/ops.json"
SYSTEM_DIGESTS = ROOT / "book/graph/mappings/system_profiles/digests.json"
RUNTIME_SIGS = ROOT / "book/graph/mappings/runtime/runtime_signatures.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def profiles_with_operation(op_name: str) -> List[str]:
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


def list_carton_paths() -> Dict[str, str]:
    return {
        "vocab_ops": str(VOCAB_OPS),
        "system_profiles": str(SYSTEM_DIGESTS),
        "runtime_signatures": str(RUNTIME_SIGS),
    }
