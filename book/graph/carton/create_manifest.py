#!/usr/bin/env python3
"""
Create the CARTON manifest for Sonoma 14.4.1.

Outputs:
- book/graph/carton/CARTON.json
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import List, Dict

ROOT = Path(__file__).resolve().parents[3]

FILES = [
    "book/graph/mappings/vocab/ops.json",
    "book/graph/mappings/vocab/filters.json",
    "book/graph/mappings/runtime/runtime_signatures.json",
    "book/graph/mappings/system_profiles/digests.json",
    "book/graph/mappings/carton/operation_coverage.json",
    "book/graph/concepts/validation/out/experiments/runtime-checks/runtime_results.normalized.json",
    "book/graph/concepts/validation/out/experiments/field2/field2_ir.json",
    "book/graph/concepts/validation/out/experiments/system-profile-digest/digests_ir.json",
    "book/graph/concepts/validation/out/vocab_status.json",
    "book/graph/concepts/validation/out/validation_status.json",
]

OUT_PATH = ROOT / "book/graph/carton/CARTON.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    rows: List[Dict[str, str]] = []
    for rel in FILES:
        p = ROOT / rel
        rows.append({"path": rel, "sha256": sha256(p)})

    meta_path = ROOT / "book/graph/concepts/validation/out/metadata.json"
    host = {}
    if meta_path.exists():
        host = json.loads(meta_path.read_text()).get("os", {})

    manifest = {
        "name": "CARTON",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": host,
        "files": rows,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(manifest, indent=2))
    print(f"[+] wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
