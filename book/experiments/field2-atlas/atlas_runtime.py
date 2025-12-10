"""
Runtime wrapper for the Field2 Atlas experiment.

This maps field2 seeds to concrete runtime probes (one per seed where available)
and emits `out/runtime/field2_runtime_results.json`. It reuses canonical runtime
signatures for this host to keep the harness field2-tagged.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from book.api import path_utils


REPO_ROOT = path_utils.find_repo_root(Path(__file__).resolve())
DEFAULT_SEEDS = Path(__file__).with_name("field2_seeds.json")
DEFAULT_RUNTIME_SIGNATURES = REPO_ROOT / "book" / "graph" / "mappings" / "runtime" / "runtime_signatures.json"
DEFAULT_OUTPUT = Path(__file__).with_name("out") / "runtime" / "field2_runtime_results.json"

# For the initial seed slice, pick one canonical runtime signature per field2.
RUNTIME_CANDIDATES = {
    0: {"profile_id": "adv:path_edges", "probe_name": "allow-tmp", "scenario_id": "field2-0-path_edges"},
    5: {"profile_id": "adv:mach_simple_allow", "probe_name": "allow-cfprefsd", "scenario_id": "field2-5-mach-global"},
    7: {"profile_id": "adv:mach_local_literal", "probe_name": "allow-cfprefsd-local", "scenario_id": "field2-7-mach-local"},
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _lookup_probe(runtime_doc: Dict[str, Any], profile_id: str, probe_name: str) -> Optional[Dict[str, Any]]:
    profile_block = runtime_doc.get("expected_matrix", {}).get("profiles", {}).get(profile_id)
    if not profile_block:
        return None
    for probe in profile_block.get("probes", []):
        if probe.get("name") == probe_name:
            return probe
    return None


def build_runtime_results(
    seeds_path: Path = DEFAULT_SEEDS,
    runtime_signatures_path: Path = DEFAULT_RUNTIME_SIGNATURES,
) -> Dict[str, Any]:
    seeds_doc = load_json(seeds_path)
    runtime_doc = load_json(runtime_signatures_path)
    signatures = runtime_doc.get("signatures") or {}
    profiles_meta = runtime_doc.get("profiles_metadata") or {}

    results = []
    for seed in seeds_doc.get("seeds", []):
        fid = seed["field2"]
        candidate = RUNTIME_CANDIDATES.get(fid)
        base_record: Dict[str, Any] = {
            "world_id": seeds_doc.get("world_id"),
            "field2": fid,
            "filter_name": seed.get("filter_name"),
            "target_ops": seed.get("target_ops") or [],
            "seed_anchors": seed.get("anchors") or [],
            "notes": seed.get("notes", ""),
        }

        if not candidate:
            base_record["status"] = "no_runtime_candidate"
            base_record["runtime_candidate"] = None
            results.append(base_record)
            continue

        profile_id = candidate["profile_id"]
        probe_name = candidate["probe_name"]
        scenario_id = candidate["scenario_id"]
        probe_info = _lookup_probe(runtime_doc, profile_id, probe_name)
        actual = (signatures.get(profile_id) or {}).get(probe_name)
        runtime_profile = profiles_meta.get(profile_id, {}).get("runtime_profile")

        if not probe_info:
            base_record["status"] = "missing_probe"
            base_record["runtime_candidate"] = candidate
            results.append(base_record)
            continue

        status = "runtime_backed" if actual is not None else "missing_actual"
        base_record.update(
            {
                "status": status,
                "runtime_candidate": {
                    "scenario_id": scenario_id,
                    "profile_id": profile_id,
                    "probe_name": probe_name,
                    "operation": probe_info.get("operation"),
                    "target": probe_info.get("target"),
                    "expected": probe_info.get("expected"),
                    "result": actual,
                    "runtime_profile": path_utils.to_repo_relative(runtime_profile, repo_root=REPO_ROOT)
                    if runtime_profile
                    else None,
                    "source": path_utils.to_repo_relative(runtime_signatures_path, repo_root=REPO_ROOT),
                },
            }
        )
        results.append(base_record)

    seed_ids = {entry["field2"] for entry in seeds_doc.get("seeds", [])}
    result_ids = {entry["field2"] for entry in results}
    if seed_ids != result_ids:
        missing = seed_ids - result_ids
        extra = result_ids - seed_ids
        raise ValueError(f"seed/runtime mismatch: missing={sorted(missing)} extra={sorted(extra)}")

    return {
        "world_id": seeds_doc.get("world_id"),
        "source_artifacts": {
            "seeds": path_utils.to_repo_relative(seeds_path, repo_root=REPO_ROOT),
            "runtime_signatures": path_utils.to_repo_relative(runtime_signatures_path, repo_root=REPO_ROOT),
        },
        "results": results,
    }


def write_results(doc: Dict[str, Any], output_path: Path = DEFAULT_OUTPUT) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)


def main() -> None:
    doc = build_runtime_results()
    write_results(doc)


if __name__ == "__main__":
    main()
