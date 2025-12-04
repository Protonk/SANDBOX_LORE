#!/usr/bin/env python3
"""
Summarize per-tag field roles (candidate filter_id vs payload) from existing artifacts.

Inputs:
- Local tag layout overrides (out/tag_layout_overrides.json)
- Field2 encoder matrix (out/field2_encoder_matrix.json)
- Optional extra blobs (tiny profiles) to observe field variability across runs

Output:
- Prints a small table per tag with:
  - candidate filter_id field (values matching filters.json)
  - candidate payload field (values that vary across probes)
  - literal_refs presence
  - supporting profiles
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple

ROOT = Path(__file__).resolve().parents[3]

def load_filters() -> Dict[int, str]:
    data = json.loads((ROOT / "book/graph/mappings/vocab/filters.json").read_text())
    return {entry["id"]: entry["name"] for entry in data.get("filters", [])}

def main() -> None:
    filters = load_filters()
    matrix = json.loads((ROOT / "book/experiments/libsandbox-encoder/out/field2_encoder_matrix.json").read_text())

    # Aggregate by tag
    agg: Dict[int, Dict[str, Any]] = defaultdict(lambda: {"filter_values": set(), "rows": [], "field_variability": defaultdict(set)})

    for row in matrix.get("rows", []):
        tag = row.get("tag")
        raw = row.get("field2_raw")
        filter_name = row.get("filter_name")
        agg[tag]["filter_values"].add((raw, filter_name))
        agg[tag]["rows"].append(row)
        # capture per-field variability
        fields: List[int] = row.get("fields", [])
        for idx, val in enumerate(fields):
            agg[tag]["field_variability"][idx].add(val)

    # Build a simple table: for each tag, list filter_id candidates and variability
    out = []
    for tag, info in sorted(agg.items()):
        filter_vals = sorted(info["filter_values"])
        literals = sum(1 for r in info["rows"] if r.get("literal_refs"))
        field_var = {str(idx): sorted(vals) for idx, vals in info["field_variability"].items()}
        out.append(
            {
                "tag": tag,
                "filter_vals": filter_vals,
                "field_variability": field_var,
                "literal_rows": literals,
                "row_count": len(info["rows"]),
            }
        )

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
