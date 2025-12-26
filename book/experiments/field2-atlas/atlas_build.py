"""
Synthesize the Field2 Atlas by merging static joins and runtime results.

Inputs:
- out/static/field2_records.jsonl (from atlas_static.py)
- out/runtime/field2_runtime_results.json (from atlas_runtime.py)

Outputs:
- out/atlas/field2_atlas.json
- out/atlas/summary.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure repository root is on sys.path for `book` imports when run directly.
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book.api import path_utils


REPO_ROOT = path_utils.find_repo_root(Path(__file__).resolve())
STATIC_PATH = Path(__file__).with_name("out") / "static" / "field2_records.jsonl"
RUNTIME_PATH = Path(__file__).with_name("out") / "runtime" / "field2_runtime_results.json"
SEEDS_PATH = Path(__file__).with_name("field2_seeds.json")
ATLAS_PATH = Path(__file__).with_name("out") / "atlas" / "field2_atlas.json"
SUMMARY_PATH = Path(__file__).with_name("out") / "atlas" / "summary.json"
SUMMARY_MD_PATH = Path(__file__).with_name("out") / "atlas" / "summary.md"


def _sha256(path: Path) -> str:
    import hashlib

    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def _load_static_records(path: Path) -> Dict[int, Dict[str, Any]]:
    records: Dict[int, Dict[str, Any]] = {}
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            record = json.loads(line)
            records[int(record["field2"])] = record
    return records


def _load_runtime_results(path: Path) -> Dict[int, Dict[str, Any]]:
    if not path.exists():
        return {}
    doc = json.loads(path.read_text())
    out: Dict[int, Dict[str, Any]] = {}
    for entry in doc.get("results", []):
        out[int(entry["field2"])] = entry
    return out


def _derive_status(static_entry: Dict[str, Any] | None, runtime_entry: Dict[str, Any] | None) -> str:
    if runtime_entry:
        status = runtime_entry.get("status")
        if status in {
            "runtime_backed",
            "runtime_backed_historical",
            "runtime_attempted_blocked",
            "missing_probe",
            "missing_actual",
            "no_runtime_candidate",
        }:
            return status
    if static_entry:
        return "static_only"
    return "unknown"


def build_atlas() -> Dict[str, Any]:
    seeds_doc = json.loads(SEEDS_PATH.read_text())
    seed_ids = {entry["field2"] for entry in seeds_doc.get("seeds", [])}
    static_records = _load_static_records(STATIC_PATH)
    runtime_results = _load_runtime_results(RUNTIME_PATH)
    field2_ids = sorted(set(static_records.keys()) | set(runtime_results.keys()))

    if seed_ids != set(field2_ids):
        missing = seed_ids - set(field2_ids)
        extra = set(field2_ids) - seed_ids
        raise ValueError(f"atlas/seed mismatch: missing={sorted(missing)} extra={sorted(extra)}")

    atlas_entries: List[Dict[str, Any]] = []
    for fid in field2_ids:
        static_entry = static_records.get(fid)
        runtime_entry = runtime_results.get(fid)
        atlas_entries.append(
            {
                "field2": fid,
                "filter_name": static_entry.get("filter_name") if static_entry else runtime_entry.get("filter_name"),
                "target_ops": (static_entry or runtime_entry or {}).get("target_ops", []),
                "static": static_entry,
                "runtime": runtime_entry,
                "status": _derive_status(static_entry, runtime_entry),
            }
        )

    summary = {"total": len(atlas_entries), "by_status": {}}
    for entry in atlas_entries:
        status = entry["status"]
        summary["by_status"][status] = summary["by_status"].get(status, 0) + 1

    # Record input metadata for sanity/debugging.
    inputs_meta = {
        "seeds": {
            "path": path_utils.to_repo_relative(SEEDS_PATH, repo_root=REPO_ROOT),
            "sha256": _sha256(SEEDS_PATH),
        },
        "static": {
            "path": path_utils.to_repo_relative(STATIC_PATH, repo_root=REPO_ROOT),
            "sha256": _sha256(STATIC_PATH),
        },
        "runtime": {
            "path": path_utils.to_repo_relative(RUNTIME_PATH, repo_root=REPO_ROOT),
            "sha256": _sha256(RUNTIME_PATH),
        },
    }

    return {
        "atlas": atlas_entries,
        "summary": summary,
        "source_artifacts": {
            "seeds": path_utils.to_repo_relative(SEEDS_PATH, repo_root=REPO_ROOT),
            "static": path_utils.to_repo_relative(STATIC_PATH, repo_root=REPO_ROOT),
            "runtime": path_utils.to_repo_relative(RUNTIME_PATH, repo_root=REPO_ROOT),
        },
        "inputs": inputs_meta,
    }


def write_outputs(doc: Dict[str, Any]) -> None:
    ATLAS_PATH.parent.mkdir(parents=True, exist_ok=True)
    ATLAS_PATH.write_text(json.dumps(doc["atlas"], indent=2, sort_keys=True), encoding="utf-8")
    SUMMARY_PATH.write_text(json.dumps(doc["summary"], indent=2, sort_keys=True), encoding="utf-8")
    # Emit a tiny markdown table for reuse elsewhere.
    lines = ["| field2 | status | profiles | anchors | runtime_scenario |", "| --- | --- | --- | --- | --- |"]
    for entry in doc["atlas"]:
        static = entry.get("static") or {}
        runtime = entry.get("runtime") or {}
        profiles = len(static.get("profiles") or [])
        anchors = len(static.get("anchor_hits") or [])
        scenario = None
        if runtime.get("runtime_candidate"):
            scenario = runtime["runtime_candidate"].get("scenario_id")
        lines.append(f"| {entry['field2']} | {entry['status']} | {profiles} | {anchors} | {scenario or ''} |")
    SUMMARY_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    doc = build_atlas()
    write_outputs(doc)


if __name__ == "__main__":
    main()
