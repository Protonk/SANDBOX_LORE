#!/usr/bin/env python3
"""
Generate mismatch packets for runtime story mismatches.

This emits a JSONL file with one packet per mismatch expectation_id, bundling
decision-stage event fields, expected entries, baseline/oracle controls, and
static witness candidates where available.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book.api import path_utils

RUNTIME_STORY = REPO_ROOT / "book/graph/mappings/runtime_cuts/runtime_story.json"
PROMOTION_PACKETS = [
    REPO_ROOT / "book/experiments/runtime-checks/out/promotion_packet.json",
    REPO_ROOT / "book/experiments/runtime-adversarial/out/promotion_packet.json",
]
FIELD2_RUNTIME = REPO_ROOT / "book/experiments/field2-atlas/out/runtime/field2_runtime_results.json"
FIELD2_STATIC = REPO_ROOT / "book/experiments/field2-atlas/out/static/field2_records.jsonl"
ANCHOR_MAP = REPO_ROOT / "book/graph/mappings/anchors/anchor_filter_map.json"
OUT = REPO_ROOT / "book/experiments/runtime-adversarial/out/mismatch_packets.jsonl"

PACKET_SCHEMA_VERSION = "runtime-mismatch-packet.v0.1"
ALLOWED_REASONS = {
    "ambient_platform_restriction",
    "path_normalization_sensitivity",
    "anchor_alias_gap",
    "expectation_too_strong",
    "capture_pipeline_disagreement",
}


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def load_promotion_paths(packet_path: Path) -> Dict[str, Path]:
    if not packet_path.exists():
        return {}
    doc = load_json(packet_path)
    paths: Dict[str, Path] = {}
    for key in ("runtime_events", "run_manifest", "baseline_results"):
        value = doc.get(key)
        if value:
            paths[key] = path_utils.ensure_absolute(Path(value), repo_root=REPO_ROOT)
    if not paths:
        return {}
    paths["promotion_packet"] = packet_path
    return paths


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_events(paths: Iterable[Path]) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        for row in load_json(path) or []:
            if isinstance(row, dict):
                row = dict(row)
                row["source"] = path_utils.to_repo_relative(path, REPO_ROOT)
                events.append(row)
    return events


def load_run_manifests(paths: Iterable[Path]) -> List[Dict[str, Any]]:
    manifests: List[Dict[str, Any]] = []
    for path in paths:
        doc = load_json(path)
        if doc:
            doc = dict(doc)
            doc["source"] = path_utils.to_repo_relative(path, REPO_ROOT)
            manifests.append(doc)
    return manifests


def index_run_manifests(manifests: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    by_run_id: Dict[str, Dict[str, Any]] = {}
    for doc in manifests:
        run_id = doc.get("run_id")
        if run_id:
            by_run_id[run_id] = doc
    return by_run_id


def build_field2_index() -> Dict[tuple[str, str], int]:
    index: Dict[tuple[str, str], int] = {}
    doc = load_json(FIELD2_RUNTIME)
    for entry in doc.get("results") or []:
        cand = entry.get("runtime_candidate") or {}
        profile_id = cand.get("profile_id")
        probe_name = cand.get("probe_name")
        field2 = entry.get("field2")
        if profile_id and probe_name is not None and field2 is not None:
            index[(profile_id, probe_name)] = int(field2)
    return index


def build_static_index() -> Dict[int, Dict[str, Any]]:
    index: Dict[int, Dict[str, Any]] = {}
    for row in load_jsonl(FIELD2_STATIC):
        fid = row.get("field2")
        if isinstance(fid, int):
            index[fid] = row
    return index


def anchor_match(anchor_map: Dict[str, Any], path: Optional[str]) -> Optional[Dict[str, Any]]:
    if not path:
        return None
    entry = anchor_map.get(path)
    if entry:
        return {"anchor": path, "entry": entry, "alias_used": False}
    if path.startswith("/private/tmp/"):
        alias = "/tmp/" + path[len("/private/tmp/") :]
        entry = anchor_map.get(alias)
        if entry:
            return {"anchor": alias, "entry": entry, "alias_used": True}
    if path == "/private/tmp":
        entry = anchor_map.get("/tmp")
        if entry:
            return {"anchor": "/tmp", "entry": entry, "alias_used": True}
    return None


def pick_callout(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    callouts = event.get("seatbelt_callouts") or []
    if not isinstance(callouts, list):
        return None
    op = event.get("operation")
    for entry in callouts:
        if isinstance(entry, dict) and entry.get("operation") == op:
            return entry
    return callouts[0] if callouts else None


def baseline_from_event(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    source = event.get("observed_path_source")
    if source == "unsandboxed_fd_path":
        return {"status": "allow", "source": "unsandboxed_fd_path"}
    if source == "unsandboxed_error":
        return {"status": "deny", "source": "unsandboxed_error"}
    return None


def classify_reason(
    *,
    baseline_status: Optional[str],
    event_decision: Optional[str],
    oracle_decision: Optional[str],
    normalized_variant: Optional[Dict[str, Any]],
    anchor_requested: Optional[Dict[str, Any]],
    anchor_normalized: Optional[Dict[str, Any]],
) -> str:
    if baseline_status == "deny":
        return "ambient_platform_restriction"
    if oracle_decision and event_decision and oracle_decision != event_decision:
        return "capture_pipeline_disagreement"
    if normalized_variant and event_decision and normalized_variant.get("actual") == event_decision:
        return "path_normalization_sensitivity"
    if anchor_requested and anchor_normalized and anchor_requested.get("anchor") != anchor_normalized.get("anchor"):
        return "anchor_alias_gap"
    return "expectation_too_strong"


def main() -> int:
    story = load_json(RUNTIME_STORY)
    if not story:
        print(f"[!] missing runtime story: {RUNTIME_STORY}")
        return 2
    packet_infos = [load_promotion_paths(path) for path in PROMOTION_PACKETS]
    packet_infos = [info for info in packet_infos if info]
    if not packet_infos:
        print("[!] missing promotion packets for runtime events")
        return 2
    event_sources = [info["runtime_events"] for info in packet_infos if "runtime_events" in info]
    run_manifest_paths = [info["run_manifest"] for info in packet_infos if "run_manifest" in info]
    baseline_paths = [info["baseline_results"] for info in packet_infos if "baseline_results" in info]
    promotion_by_manifest = {
        path_utils.to_repo_relative(info["run_manifest"], REPO_ROOT): path_utils.to_repo_relative(
            info["promotion_packet"], REPO_ROOT
        )
        for info in packet_infos
        if "run_manifest" in info
    }

    events = load_events(event_sources)
    events_by_expectation = {e.get("expectation_id"): e for e in events if e.get("expectation_id")}
    events_by_probe = {(e.get("profile_id"), e.get("probe_name")): e for e in events if e.get("profile_id")}
    run_manifest_list = load_run_manifests(run_manifest_paths)
    for doc in run_manifest_list:
        source = doc.get("source")
        if source and source in promotion_by_manifest:
            doc["promotion_packet"] = promotion_by_manifest[source]
    run_manifests = index_run_manifests(run_manifest_list)
    baseline_by_name: Dict[str, Any] = {}
    for baseline_path in baseline_paths:
        baseline_doc = load_json(baseline_path)
        for row in (baseline_doc.get("results") or []):
            if isinstance(row, dict) and row.get("name"):
                baseline_by_name[row.get("name")] = row
    field2_by_probe = build_field2_index()
    static_by_field2 = build_static_index()
    anchor_map = load_json(ANCHOR_MAP)

    packets = []
    for op_entry in (story.get("ops") or {}).values():
        for scenario in op_entry.get("scenarios") or []:
            mismatches = scenario.get("mismatches") or []
            for mismatch in mismatches:
                eid = mismatch.get("expectation_id")
                if not eid:
                    continue
                event = events_by_expectation.get(eid)
                if not event:
                    raise RuntimeError(f"missing event for mismatch expectation_id={eid}")
                run_id = event.get("run_id")
                manifest = run_manifests.get(run_id) if run_id else None
                if not manifest:
                    source = event.get("source") or ""
                    for doc in run_manifest_list:
                        doc_source = doc.get("source") or ""
                        if "runtime-adversarial" in source and "runtime-adversarial" in doc_source:
                            manifest = doc
                            break
                        if "runtime-checks" in source and "runtime-checks" in doc_source:
                            manifest = doc
                            break

                profile_id = event.get("profile_id")
                probe_name = event.get("probe_name")
                baseline_key = f"baseline:{profile_id}:{probe_name}"
                baseline = baseline_by_name.get(baseline_key)
                if not baseline:
                    baseline = baseline_from_event(event)

                callout = pick_callout(event)
                oracle_decision = callout.get("decision") if isinstance(callout, dict) else None

                normalized_variant = None
                if profile_id == "adv:path_edges" and probe_name == "allow-subpath":
                    normalized_variant = events_by_probe.get((profile_id, "allow-subpath-normalized"))

                expected_anchor = anchor_match(anchor_map, event.get("target"))
                normalized_anchor = anchor_match(anchor_map, event.get("normalized_path"))

                field2 = field2_by_probe.get((profile_id, probe_name))
                static_candidates = static_by_field2.get(field2) if field2 is not None else None

                reason = classify_reason(
                    baseline_status=(baseline.get("status") if isinstance(baseline, dict) else None),
                    event_decision=event.get("actual"),
                    oracle_decision=oracle_decision,
                    normalized_variant=normalized_variant,
                    anchor_requested=expected_anchor,
                    anchor_normalized=normalized_anchor,
                )
                if reason not in ALLOWED_REASONS:
                    reason = "expectation_too_strong"

                packet = {
                    "schema_version": PACKET_SCHEMA_VERSION,
                    "expectation_id": eid,
                    "run_context": {
                        "run_id": run_id,
                        "channel": (manifest or {}).get("channel"),
                        "world_id": event.get("world_id"),
                        "repo_root_context": (manifest or {}).get("repo_root_context"),
                        "run_manifest": (manifest or {}).get("source"),
                        "promotion_packet": (manifest or {}).get("promotion_packet"),
                    },
                    "decision_event": {
                        "scenario_id": event.get("scenario_id"),
                        "profile_id": profile_id,
                        "probe_name": probe_name,
                        "operation": event.get("operation"),
                        "requested_path": event.get("requested_path"),
                        "observed_path": event.get("observed_path"),
                        "normalized_path": event.get("normalized_path"),
                        "runtime_status": event.get("runtime_status"),
                        "failure_stage": event.get("failure_stage"),
                        "failure_kind": event.get("failure_kind"),
                        "decision": event.get("actual"),
                        "errno": event.get("errno"),
                        "source": event.get("source"),
                        "filter_type": callout.get("filter_type") if isinstance(callout, dict) else None,
                        "filter_type_name": callout.get("filter_type_name") if isinstance(callout, dict) else None,
                    },
                    "expected": {
                        "expectation_id": eid,
                        "expected_decision": event.get("expected"),
                        "target": event.get("target"),
                        "anchor_binding": expected_anchor,
                    },
                    "baseline": baseline,
                    "normalization_control": normalized_variant,
                    "oracle_check": {
                        "decision": oracle_decision,
                        "stage": callout.get("stage") if isinstance(callout, dict) else None,
                        "filter_type": callout.get("filter_type") if isinstance(callout, dict) else None,
                        "filter_type_name": callout.get("filter_type_name") if isinstance(callout, dict) else None,
                        "argument": callout.get("argument") if isinstance(callout, dict) else None,
                    }
                    if callout
                    else None,
                    "mismatch_reason": reason,
                    "field2_static_candidates": static_candidates,
                    "field2": field2,
                }
                packets.append(packet)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(json.dumps(p, sort_keys=True) for p in packets) + "\n")
    print(f"[+] wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
