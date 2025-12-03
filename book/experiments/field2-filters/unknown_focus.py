#!/usr/bin/env python3
"""
Emit focused details for nodes with high/unknown field2 values, including fan-in/out counts
based on tag layouts (edge fields) and basic literal references.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import sys
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import book.api.decoder as decoder  # type: ignore


def load_layouts() -> Dict[int, Dict[str, Any]]:
    path = Path("book/graph/mappings/tag_layouts/tag_layouts.json")
    data = json.loads(path.read_text())
    return {rec["tag"]: rec for rec in data.get("tags", [])}


def edge_fields_for(tag: int, layouts: Dict[int, Dict[str, Any]]) -> List[int]:
    rec = layouts.get(tag)
    if not rec:
        return []
    return rec.get("edge_fields", [])


def summarize_profile(path: Path, filter_names: Dict[int, str], layouts: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
    prof = decoder.decode_profile_dict(path.read_bytes())
    nodes = prof.get("nodes") or []
    # Build fan-in counts
    fan_in: Dict[int, int] = {}
    for idx, node in enumerate(nodes):
        fields = node.get("fields", [])
        edges = [fields[i] for i in edge_fields_for(node.get("tag", -1), layouts) if i < len(fields)]
        for e in edges:
            fan_in[e] = fan_in.get(e, 0) + 1

    unknowns: List[Dict[str, Any]] = []
    for idx, node in enumerate(nodes):
        fields = node.get("fields", [])
        if len(fields) < 3:
            continue
        raw = fields[2]
        hi = raw & 0xC000
        lo = raw & 0x3FFF
        name = filter_names.get(lo) if hi == 0 else None
        if hi != 0 or name is None:
            edges = [fields[i] for i in edge_fields_for(node.get("tag", -1), layouts) if i < len(fields)]
            unknowns.append(
                {
                    "idx": idx,
                    "tag": node.get("tag"),
                    "fields": fields,
                    "edges": edges,
                    "fan_out": len([e for e in edges if 0 <= e < len(nodes)]),
                    "fan_in": fan_in.get(idx, 0),
                    "raw": raw,
                    "raw_hex": hex(raw),
                    "hi": hi,
                    "lo": lo,
                    "name_lo": name,
                    "literal_refs": node.get("literal_refs", []),
                }
            )
    return {"path": str(path), "unknown_nodes": unknowns}


def main() -> None:
    filter_names = {entry["id"]: entry["name"] for entry in json.loads(Path("book/graph/mappings/vocab/filters.json").read_text()).get("filters", [])}
    layouts = load_layouts()
    profiles = [
        Path("book/examples/extract_sbs/build/profiles/bsd.sb.bin"),
        Path("book/examples/extract_sbs/build/profiles/airlock.sb.bin"),
        Path("book/examples/sb/build/sample.sb.bin"),
        Path("book/experiments/probe-op-structure/sb/build/v4_network_socket_require_all.sb.bin"),
        Path("book/experiments/probe-op-structure/sb/build/v7_file_network_combo.sb.bin"),
    ]
    out: Dict[str, Any] = {}
    for p in profiles:
        if not p.exists():
            continue
        rec = summarize_profile(p, filter_names, layouts)
        out[p.stem] = rec["unknown_nodes"]
    out_dir = Path("book/experiments/field2-filters/out")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "unknown_nodes.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    print(f"[+] wrote {out_path}")


if __name__ == "__main__":
    main()
