#!/usr/bin/env python3
"""Generate mismatch packets for hardened-runtime mismatches."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book.api import path_utils

OUT_DIR = REPO_ROOT / "book/experiments/hardened-runtime/out"
MISMATCH_SUMMARY = OUT_DIR / "mismatch_summary.json"
EVENTS = OUT_DIR / "runtime_events.normalized.json"
BASELINE = OUT_DIR / "baseline_results.json"
RUN_MANIFEST = OUT_DIR / "run_manifest.json"
OUT = OUT_DIR / "mismatch_packets.jsonl"

PACKET_SCHEMA_VERSION = "hardened-runtime-mismatch-packet.v0.1"
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


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def pick_callout(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    callouts = event.get("seatbelt_callouts") or []
    if not isinstance(callouts, list):
        return None
    op = event.get("operation")
    for entry in callouts:
        if isinstance(entry, dict) and entry.get("operation") == op:
            return entry
    return callouts[0] if callouts else None


def classify_reason(
    *,
    baseline_status: Optional[str],
    event_decision: Optional[str],
    oracle_decision: Optional[str],
) -> str:
    if baseline_status == "deny":
        return "ambient_platform_restriction"
    if oracle_decision and event_decision and oracle_decision != event_decision:
        return "capture_pipeline_disagreement"
    return "expectation_too_strong"


def main() -> int:
    mismatch_doc = load_json(MISMATCH_SUMMARY)
    if not mismatch_doc:
        print(f"[!] missing mismatch summary: {MISMATCH_SUMMARY}")
        return 2
    events = load_json(EVENTS)
    events_by_eid = {row.get("expectation_id"): row for row in events if row.get("expectation_id")}
    baseline_doc = load_json(BASELINE)
    baseline_by_name = {row.get("name"): row for row in (baseline_doc.get("results") or []) if isinstance(row, dict)}
    manifest = load_json(RUN_MANIFEST)

    packets = []
    for mismatch in mismatch_doc.get("mismatches") or []:
        eid = mismatch.get("expectation_id")
        if not eid:
            continue
        event = events_by_eid.get(eid)
        if not event:
            raise RuntimeError(f"missing event for mismatch expectation_id={eid}")
        profile_id = event.get("profile_id")
        probe_name = event.get("probe_name")
        baseline_key = f"baseline:{profile_id}:{probe_name}"
        baseline = baseline_by_name.get(baseline_key)

        callout = pick_callout(event)
        oracle_decision = callout.get("decision") if isinstance(callout, dict) else None
        reason = classify_reason(
            baseline_status=(baseline.get("status") if isinstance(baseline, dict) else None),
            event_decision=event.get("actual"),
            oracle_decision=oracle_decision,
        )
        if reason not in ALLOWED_REASONS:
            reason = "expectation_too_strong"

        packet = {
            "schema_version": PACKET_SCHEMA_VERSION,
            "expectation_id": eid,
            "run_context": {
                "run_id": event.get("run_id"),
                "channel": manifest.get("channel") if manifest else None,
                "world_id": event.get("world_id"),
                "repo_root_context": manifest.get("repo_root_context") if manifest else None,
                "run_manifest": path_utils.to_repo_relative(RUN_MANIFEST, repo_root=REPO_ROOT) if RUN_MANIFEST.exists() else None,
            },
            "decision_event": {
                "scenario_id": event.get("scenario_id"),
                "profile_id": profile_id,
                "probe_name": probe_name,
                "operation": event.get("operation"),
                "target": event.get("target"),
                "requested_path": event.get("requested_path"),
                "observed_path": event.get("observed_path"),
                "normalized_path": event.get("normalized_path"),
                "runtime_status": event.get("runtime_status"),
                "failure_stage": event.get("failure_stage"),
                "failure_kind": event.get("failure_kind"),
                "decision": event.get("actual"),
                "errno": event.get("errno"),
                "source": path_utils.to_repo_relative(EVENTS, repo_root=REPO_ROOT),
                "filter_type": callout.get("filter_type") if isinstance(callout, dict) else None,
                "filter_type_name": callout.get("filter_type_name") if isinstance(callout, dict) else None,
            },
            "expected": {
                "expectation_id": eid,
                "expected_decision": mismatch.get("expected"),
                "target": mismatch.get("path") or event.get("target"),
            },
            "baseline": baseline,
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
        }
        packets.append(packet)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(json.dumps(p, sort_keys=True) for p in packets) + "\n")
    print(f"[+] wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
