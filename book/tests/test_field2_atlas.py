import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_json(path: Path):
    assert path.exists(), f"missing expected file: {path}"
    return json.loads(path.read_text())


def load_jsonl(path: Path):
    assert path.exists(), f"missing expected file: {path}"
    records = []
    for line in path.read_text().splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def test_field2_atlas_covers_seed_set_and_runtime():
    seeds_doc = load_json(ROOT / "book" / "experiments" / "field2-atlas" / "field2_seeds.json")
    seeds = seeds_doc.get("seeds") or []
    seed_ids = {entry["field2"] for entry in seeds}

    # Seed manifest must be stable and contain the anchor-backed baseline slice.
    assert seeds, "expected a non-empty seed manifest"
    assert {0, 5, 7}.issubset(seed_ids), "baseline field2 seeds should remain present"

    atlas_entries = load_json(ROOT / "book" / "experiments" / "field2-atlas" / "out" / "atlas" / "field2_atlas.json")
    atlas_ids = {entry["field2"] for entry in atlas_entries}

    # The atlas must carry every seed (no dropouts).
    assert seed_ids == atlas_ids, f"atlas missing seeds: {sorted(seed_ids - atlas_ids)}"
    allowed_statuses = {"runtime_backed", "static_only", "no_runtime_candidate", "missing_probe", "missing_actual"}
    assert all(entry.get("status") in allowed_statuses for entry in atlas_entries), "unexpected atlas status present"

    static_records = load_jsonl(ROOT / "book" / "experiments" / "field2-atlas" / "out" / "static" / "field2_records.jsonl")
    static_by_id = {entry["field2"]: entry for entry in static_records}
    for fid in seed_ids:
        assert fid in static_by_id, f"no static record for seed field2={fid}"
        # Each static record should retain at least one anchor or profile witness.
        has_anchor = bool(static_by_id[fid].get("anchor_hits"))
        has_profile = bool(static_by_id[fid].get("profiles"))
        assert has_anchor or has_profile, f"seed field2={fid} missing static witnesses"

    runtime_doc = load_json(ROOT / "book" / "experiments" / "field2-atlas" / "out" / "runtime" / "field2_runtime_results.json")
    runtime_results = runtime_doc.get("results") or []
    runtime_backed = [entry for entry in runtime_results if entry.get("status") == "runtime_backed"]
    no_runtime_candidate = [entry for entry in runtime_results if entry.get("status") == "no_runtime_candidate"]

    # At least one seed must be runtime-backed, and none should silently drop unless explicitly marked.
    assert runtime_backed, "expected at least one runtime-backed seed"

    # Baseline seeds must stay runtime-backed; later seeds can be static-only/no-runtime.
    for fid in (0, 5, 7):
        entry = next((e for e in runtime_results if e.get("field2") == fid), None)
        assert entry and entry.get("status") == "runtime_backed", f"baseline seed {fid} not runtime_backed"

    candidate = runtime_backed[0].get("runtime_candidate") or {}
    source_rel = candidate.get("source")
    assert source_rel, "runtime candidate missing source reference"
    source_path = ROOT / source_rel
    assert source_path.exists(), f"runtime signature source missing: {source_path}"

    runtime_signatures = load_json(source_path)
    profile_id = candidate.get("profile_id")
    probe_name = candidate.get("probe_name")
    actual = candidate.get("result")

    assert profile_id and probe_name, "runtime candidate missing profile/probe identifiers"
    recorded_actual = (runtime_signatures.get("signatures") or {}).get(profile_id, {}).get(probe_name)
    assert recorded_actual == actual, (
        f"runtime result for {profile_id}:{probe_name} does not match runtime_signatures "
        f"(result={actual}, runtime_signatures={recorded_actual})"
    )

    # Summary should mirror atlas statuses.
    summary = load_json(ROOT / "book" / "experiments" / "field2-atlas" / "out" / "atlas" / "summary.json")
    total_from_status = sum(summary.get("by_status", {}).values())
    assert total_from_status == summary.get("total"), "summary total does not match by_status counts"
    assert total_from_status == len(atlas_entries), "summary total does not match atlas entries"
