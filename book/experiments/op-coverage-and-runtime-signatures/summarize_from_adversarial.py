from __future__ import annotations
import json
import sys
from pathlib import Path

from book.api import path_utils

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = Path(__file__).resolve().parent / "out"
OUT_DIR.mkdir(exist_ok=True)

LOCAL_RESULTS = OUT_DIR / "runtime_results.json"
LOCAL_EXPECTED = OUT_DIR / "expected_matrix.json"
LOCAL_EVENTS = OUT_DIR / "runtime_events.normalized.json"
PROMOTION_PACKET = ROOT / "book" / "experiments" / "runtime-adversarial" / "out" / "promotion_packet.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from book.api.runtime_tools.core.models import WORLD_ID, RuntimeObservation
from book.api.runtime_tools.core.normalize import normalize_matrix_paths, observation_to_dict
from book.api.runtime_tools.mapping import build as mapping_build
from book.api.runtime_tools import workflow

BLOCKED_STAGES = {"apply", "bootstrap", "preflight"}


def _pick_path(candidates: list[Path]) -> Path:
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(f"None of the candidate paths exist: {candidates}")


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _load_promotion_packet() -> dict:
    if not PROMOTION_PACKET.exists():
        return {}
    return _load_json(PROMOTION_PACKET)


def load_expected_and_results() -> tuple[dict, dict, Path, Path]:
    packet = _load_promotion_packet()
    packet_results = packet.get("runtime_results")
    packet_expected = packet.get("expected_matrix")
    if packet_results and packet_expected:
        runtime_results_path = path_utils.ensure_absolute(Path(packet_results), repo_root=ROOT)
        expected_path = path_utils.ensure_absolute(Path(packet_expected), repo_root=ROOT)
        return _load_json(expected_path), _load_json(runtime_results_path), expected_path, runtime_results_path
    runtime_results_path = _pick_path([LOCAL_RESULTS])
    expected_path = _pick_path([LOCAL_EXPECTED])
    return _load_json(expected_path), _load_json(runtime_results_path), expected_path, runtime_results_path


def load_observations() -> list[dict]:
    # Prefer pre-normalized events if present; otherwise normalize on the fly.
    packet = _load_promotion_packet()
    packet_events = packet.get("runtime_events")
    if packet_events:
        return _load_json(path_utils.ensure_absolute(Path(packet_events), repo_root=ROOT))
    if LOCAL_EVENTS.exists():
        return _load_json(LOCAL_EVENTS)

    expected_doc, runtime_doc, expected_path, results_path = load_expected_and_results()
    world_id = expected_doc.get("world_id") or runtime_doc.get("world_id") or WORLD_ID
    obs = normalize_matrix_paths(expected_path, results_path, world_id=world_id)
    return [observation_to_dict(o) for o in obs]


observations = load_observations()


def build_reference_op_summary(observations: list[RuntimeObservation]) -> dict:
    """
    Build an independent per-op summary from observations to compare against
    the canonical op mapping. Keeps full scenario sets and counts (no truncation).
    """

    ref: dict[str, dict] = {}
    for obs in observations:
        entry = ref.setdefault(
            obs.operation,
            {
                "probes": 0,
                "matches": 0,
                "mismatches": 0,
                "probes_including_blocked": 0,
                "blocked": {"total": 0, "by_stage": {}, "by_kind": {}},
                "scenarios": set(),
            },
        )
        entry["probes_including_blocked"] += 1
        entry["scenarios"].add(obs.scenario_id)
        if (obs.failure_stage or "probe") in BLOCKED_STAGES:
            blocked = entry["blocked"]
            blocked["total"] += 1
            stage = obs.failure_stage or "unknown"
            by_stage = blocked["by_stage"]
            by_stage[stage] = int(by_stage.get(stage, 0)) + 1
            if obs.failure_kind:
                by_kind = blocked["by_kind"]
                by_kind[obs.failure_kind] = int(by_kind.get(obs.failure_kind, 0)) + 1
            continue
        entry["probes"] += 1
        if obs.match:
            entry["matches"] += 1
        else:
            entry["mismatches"] += 1

    for op_name, entry in ref.items():
        entry["scenarios"] = sorted(entry["scenarios"])
        if entry["mismatches"] == 0 and entry["probes"] > 0:
            entry["coverage_status"] = "ok"
        elif entry["probes"] > 0:
            entry["coverage_status"] = "partial"
        else:
            entry["coverage_status"] = "brittle"
    return ref

# Preferred path: build canonical op mapping from events index if present.
events_index_candidates = [
    ROOT / "book" / "graph" / "mappings" / "runtime_cuts" / "events_index.json",
    OUT_DIR / "runtime_mappings" / "events_index.json",
]
canonical_op = None
for candidate in events_index_candidates:
    if candidate.exists():
        canonical_op = workflow.build_ops_from_index(candidate, world_id=WORLD_ID)
        break

if canonical_op is None:
    # Fallback: build from normalized observations directly.
    obs_objs = [RuntimeObservation(**o) for o in observations]
    canonical_op = mapping_build.build_ops(obs_objs, world_id=WORLD_ID)
else:
    obs_objs = [RuntimeObservation(**o) for o in observations]

if isinstance(canonical_op, dict) and canonical_op.get("ops"):
    canonical_path = OUT_DIR / "runtime_mappings" / "ops.json"
    canonical_path.parent.mkdir(parents=True, exist_ok=True)
    canonical_path.write_text(json.dumps(canonical_op, indent=2))
    print(f"Wrote canonical op mapping to {canonical_path}")
    # Guardrail: compare against a full reference built directly from observations.
    reference = build_reference_op_summary(obs_objs)
    canonical_ops = canonical_op.get("ops") or {}
    errors = []
    if set(reference.keys()) != set(canonical_ops.keys()):
        missing = set(reference.keys()) - set(canonical_ops.keys())
        extra = set(canonical_ops.keys()) - set(reference.keys())
        if missing:
            errors.append(f"canonical ops missing entries: {sorted(missing)}")
        if extra:
            errors.append(f"canonical ops contained unexpected entries: {sorted(extra)}")
    for op_name, ref_entry in reference.items():
        canon_entry = canonical_ops.get(op_name) or {}
        for field in ["probes", "matches", "mismatches", "probes_including_blocked"]:
            if ref_entry.get(field) != canon_entry.get(field):
                errors.append(f"{op_name} {field} mismatch: ref={ref_entry.get(field)} canon={canon_entry.get(field)}")
        if ref_entry.get("blocked") != canon_entry.get("blocked"):
            errors.append(f"{op_name} blocked mismatch: ref={ref_entry.get('blocked')} canon={canon_entry.get('blocked')}")
        if set(ref_entry.get("scenarios") or []) != set(canon_entry.get("scenarios") or []):
            errors.append(
                f"{op_name} scenario set mismatch: ref={sorted(ref_entry.get('scenarios') or [])} canon={sorted(canon_entry.get('scenarios') or [])}"
            )
        if ref_entry.get("coverage_status") != canon_entry.get("coverage_status"):
            errors.append(
                f"{op_name} coverage status mismatch: ref={ref_entry.get('coverage_status')} canon={canon_entry.get('coverage_status')}"
            )
    if errors:
        raise SystemExit(f"canonical op mapping guardrail failed: {errors}")
else:
    print("[!] Failed to build canonical op mapping; skipping guardrail")

def build_op_runtime_summary(observations: list[RuntimeObservation]) -> dict:
    summary: dict[str, dict] = {}
    for obs in observations:
        entry = summary.setdefault(
            obs.operation,
            {
                "probes": 0,
                "matches": 0,
                "mismatches": 0,
                "probes_including_blocked": 0,
                "blocked": {"total": 0, "by_stage": {}, "by_kind": {}},
                "examples": [],
                "mismatch_details": [],
            },
        )
        entry["probes_including_blocked"] += 1
        if (obs.failure_stage or "probe") in BLOCKED_STAGES:
            blocked = entry["blocked"]
            blocked["total"] += 1
            stage = obs.failure_stage or "unknown"
            by_stage = blocked["by_stage"]
            by_stage[stage] = int(by_stage.get(stage, 0)) + 1
            if obs.failure_kind:
                by_kind = blocked["by_kind"]
                by_kind[obs.failure_kind] = int(by_kind.get(obs.failure_kind, 0)) + 1
            continue

        entry["probes"] += 1
        if obs.match:
            entry["matches"] += 1
        else:
            entry["mismatches"] += 1
            entry["mismatch_details"].append(
                {
                    "profile": obs.profile_id,
                    "expectation_id": obs.expectation_id,
                    "expected": obs.expected,
                    "actual": obs.actual,
                    "path": obs.target,
                }
            )
        if len(entry["examples"]) < 5:
            entry["examples"].append(
                {
                    "profile": obs.profile_id,
                    "expectation_id": obs.expectation_id,
                    "expected": obs.expected,
                    "actual": obs.actual,
                    "match": obs.match,
                }
            )
    return summary

# Emit canonical runtime mapping shapes into this experiment's staging area.
try:
    expected_doc, _, expected_path, _ = load_expected_and_results()
    mapping_root = OUT_DIR / "runtime_mappings"
    traces_dir = mapping_root / "traces"

    events_index, _ = mapping_build.write_traces(
        [RuntimeObservation(**o) for o in observations],
        traces_dir,
        world_id=WORLD_ID,
    )
    events_index_path = mapping_root / "events_index.json"
    mapping_build.write_events_index(events_index, events_index_path)

    scenario_doc = mapping_build.build_scenarios(
        [RuntimeObservation(**o) for o in observations],
        expected_doc,
        world_id=WORLD_ID,
    )
    scenario_path = mapping_root / "scenarios.json"
    mapping_build.write_scenarios(scenario_doc, scenario_path)

    op_doc = mapping_build.build_ops(
        [RuntimeObservation(**o) for o in observations],
        world_id=WORLD_ID,
    )
    op_path = mapping_root / "ops.json"
    mapping_build.write_ops(op_doc, op_path)

    idx_doc = mapping_build.build_indexes(scenario_doc, events_index)
    idx_path = mapping_root / "runtime_indexes.json"
    mapping_build.write_indexes(idx_doc, idx_path)

    manifest = mapping_build.build_manifest(WORLD_ID, events_index_path, scenario_path, op_path)
    manifest_path = mapping_root / "runtime_manifest.json"
    mapping_build.write_manifest(manifest, manifest_path)
    print(f"Wrote staged runtime mappings under {mapping_root}")
except Exception as e:
    print(f"[!] failed to emit staged runtime mappings: {e}")

summary_path = OUT_DIR / "op_runtime_summary.json"
summary_path.write_text(json.dumps(build_op_runtime_summary(obs_objs), indent=2))
print(f"Wrote per-op runtime summary to {summary_path}")
