#!/usr/bin/env python3
"""
Decode the runtime-checks golden profiles into a stable summary JSON.

Outputs:
- out/decoded_blobs/<key>.sb.bin – compiled blobs for SBPL profiles.
- out/golden_decodes.json – decoder summaries (node_count, op_count, tag_counts, literal_strings).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from book.api import decoder
from book.api.sbpl_compile import compile_sbpl_string

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
MATRIX = OUT / "expected_matrix.json"
DECODE_OUT = OUT / "golden_decodes.json"
DECODED_BLOBS = OUT / "decoded_blobs"

# Fixed golden set for runtime-checks.
GOLDEN_KEYS = [
    "bucket4:v1_read",
    "bucket5:v11_read_subpath",
    "runtime:metafilter_any",
    "runtime:strict_1",
    "sys:bsd",
    "sys:airlock",
]


def load_matrix() -> Dict[str, Dict]:
    assert MATRIX.exists(), f"missing expected_matrix.json at {MATRIX}"
    data = json.loads(MATRIX.read_text())
    return data.get("profiles") or {}


def compile_profile(path: Path) -> bytes:
    if path.suffix == ".bin":
        return path.read_bytes()
    # SBPL source
    return compile_sbpl_string(path.read_text()).blob


def main() -> int:
    profiles = load_matrix()
    DECODED_BLOBS.mkdir(parents=True, exist_ok=True)
    results: List[Dict] = []
    for key in GOLDEN_KEYS:
        rec = profiles.get(key)
        if not rec:
            raise SystemExit(f"missing profile {key} in expected_matrix.json")
        blob_path = Path(rec["blob"])
        blob_bytes = compile_profile(blob_path)
        out_blob = DECODED_BLOBS / f"{key.replace(':', '_')}.sb.bin"
        out_blob.write_bytes(blob_bytes)
        decoded = decoder.decode_profile_dict(blob_bytes)
        results.append(
            {
                "key": key,
                "blob": str(blob_path),
                "compiled_blob": str(out_blob),
                "node_count": decoded.get("node_count"),
                "op_count": decoded.get("op_count"),
                "tag_counts": decoded.get("tag_counts"),
                "literal_strings": decoded.get("literal_strings"),
            }
        )
    DECODE_OUT.write_text(json.dumps(results, indent=2))
    print(f"[+] wrote {DECODE_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
