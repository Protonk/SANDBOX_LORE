#!/usr/bin/env python3
"""
Collect field2 inventories for quick comparison.

Outputs per-profile:
- op_count, node_count
- field2 histogram
- optional name mapping via filters.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List

import sys
ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import book.api.decoder as decoder  # type: ignore


def load_filters() -> Dict[int, str]:
    path = Path("book/graph/mappings/vocab/filters.json")
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    return {entry["id"]: entry["name"] for entry in data.get("filters", [])}


def summarize_profile(path: Path, filter_names: Dict[int, str]) -> Dict[str, Any]:
    prof = decoder.decode_profile_dict(path.read_bytes())
    nodes = prof.get("nodes") or []
    hist: Dict[int, int] = {}
    for node in nodes:
        fields = node.get("fields", [])
        if len(fields) > 2:
            val = fields[2]
            hist[val] = hist.get(val, 0) + 1
    return {
        "op_count": prof.get("op_count"),
        "node_count": prof.get("node_count"),
        "field2": [
            {
                "value": v,
                "count": c,
                "name": filter_names.get(v),
            }
            for v, c in sorted(hist.items(), key=lambda x: -x[1])
        ],
    }


def main() -> None:
    filter_names = load_filters()
    profiles: Dict[str, Path] = {
        "sys:airlock": Path("book/examples/extract_sbs/build/profiles/airlock.sb.bin"),
        "sys:bsd": Path("book/examples/extract_sbs/build/profiles/bsd.sb.bin"),
        "sys:sample": Path("book/examples/sb/build/sample.sb.bin"),
    }

    # Pull in the single-filter probes for this experiment
    probes_dir = Path("book/experiments/field2-filters/sb/build")
    if probes_dir.exists():
        for p in sorted(probes_dir.glob("*.sb.bin")):
            profiles[f"probe:{p.stem}"] = p

    out = {
        name: summarize_profile(path, filter_names)
        for name, path in profiles.items()
        if path.exists()
    }

    out_dir = Path("book/experiments/field2-filters/out")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "field2_inventory.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    print(f"[+] wrote {out_path}")


if __name__ == "__main__":
    main()
