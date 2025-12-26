import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STORY = ROOT / "book" / "graph" / "mappings" / "runtime_cuts" / "runtime_story.json"
PACKETS = ROOT / "book" / "experiments" / "runtime-adversarial" / "out" / "mismatch_packets.jsonl"
ALLOWED_REASONS = {
    "ambient_platform_restriction",
    "path_normalization_sensitivity",
    "anchor_alias_gap",
    "expectation_too_strong",
    "capture_pipeline_disagreement",
}


def load_json(path: Path):
    assert path.exists(), f"missing required file: {path}"
    return json.loads(path.read_text())


def load_jsonl(path: Path):
    assert path.exists(), f"missing mismatch packets: {path}"
    rows = []
    for line in path.read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _story_mismatches(story_doc):
    mismatches = set()
    for op_entry in (story_doc.get("ops") or {}).values():
        for scenario in op_entry.get("scenarios") or []:
            for mismatch in scenario.get("mismatches") or []:
                eid = mismatch.get("expectation_id")
                if eid:
                    mismatches.add(eid)
    return mismatches


def test_mismatch_packets_cover_story_mismatches():
    story_doc = load_json(STORY)
    mismatch_ids = _story_mismatches(story_doc)
    packets = load_jsonl(PACKETS)
    packet_ids = {row.get("expectation_id") for row in packets if row.get("expectation_id")}
    missing = mismatch_ids - packet_ids
    assert not missing, f"missing mismatch packets for {len(missing)} expectations: {sorted(missing)[:5]}"
    for row in packets:
        reason = row.get("mismatch_reason")
        assert reason in ALLOWED_REASONS, f"unexpected mismatch_reason: {reason}"
