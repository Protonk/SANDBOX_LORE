"""
Canonical runtime observation schema and helpers for scenario identity.

This module does not execute probes; it normalizes harness output
(`runtime_results.json` + `expected_matrix.json`) into a single observation
shape with stable scenario IDs keyed to this world's runtime work. Full event
logs are treated as recomputable; callers can write small curated slices when
needed, but the normalization helpers are the source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from book.api import path_utils

# Fixed world for this repository.
WORLD_ID = "sonoma-14.4.1-23E224-arm64-dyld-2c0602c5"


@dataclass
class RuntimeObservation:
    """
    Canonical per-event runtime record for this world.

    Fields are intentionally redundant with the harness output so that a single
    observation carries enough context to stand alone or to be joined back to
    expectations and static mappings.
    """

    world_id: str
    profile_id: str
    scenario_id: str
    expectation_id: Optional[str] = None
    operation: str = ""
    target: Optional[str] = None
    probe_name: Optional[str] = None
    expected: Optional[str] = None
    actual: Optional[str] = None
    match: Optional[bool] = None
    runtime_status: Optional[str] = None
    errno: Optional[int] = None
    errno_name: Optional[str] = None
    failure_stage: Optional[str] = None
    failure_kind: Optional[str] = None
    apply_report: Optional[Dict[str, Any]] = None
    violation_summary: Optional[str] = None
    command: Optional[List[str]] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    harness: Optional[str] = None
    notes: Optional[str] = None


def _strip_sbpl_apply_markers(stderr: Optional[str]) -> Optional[str]:
    """
    Remove sbpl-apply JSONL stage markers from stderr.

    Markers are inputs to normalization/classification, not part of the canonical
    normalized runtime IR payload.
    """

    if not stderr:
        return stderr
    kept: List[str] = []
    for line in stderr.splitlines():
        candidate = line.strip()
        if candidate.startswith("{") and candidate.endswith("}"):
            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError:
                payload = None
            if (
                isinstance(payload, dict)
                and payload.get("tool") == "sbpl-apply"
                and payload.get("stage") in {"apply", "applied", "exec"}
            ):
                continue
        kept.append(line)
    if not kept:
        return ""
    return "\n".join(kept) + ("\n" if stderr.endswith("\n") else "")


def derive_expectation_id(profile_id: str, operation: Optional[str], target: Optional[str]) -> str:
    """
    Fallback expectation identifier when one is not present in the matrix.

    Mirrors the provisional pattern described in runtime_log_schema.v0.1.json:
    profile_id|op|path. Keeps simple separators to avoid collisions.
    """

    op_part = operation or "op"
    target_part = target or "target"
    return "|".join([profile_id, op_part, target_part])


def make_scenario_id(
    world_id: str,
    profile_id: str,
    probe_name: Optional[str] = None,
    expectation_id: Optional[str] = None,
    operation: Optional[str] = None,
    target: Optional[str] = None,
) -> str:
    """
    Build a stable scenario_id for runtime traces.

    Priority:
    1. If expectation_id exists, reuse it (most stable link to expectations).
    2. Else, use profile_id + probe_name when available.
    3. Else, fall back to profile_id + op + target.
    World is carried separately; do not bake it into the ID.
    """

    if expectation_id:
        return expectation_id
    if probe_name:
        return f"{profile_id}::{probe_name}"
    op_part = operation or "op"
    target_part = target or "target"
    return f"{profile_id}::{op_part}::{target_part}"


def serialize_observation(obs: RuntimeObservation) -> Dict[str, Any]:
    """
    Serialize an observation to a JSON-friendly dict, dropping None values.
    """

    raw = asdict(obs)
    return {k: v for k, v in raw.items() if v is not None}


def _index_expectations(matrix: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Build lookup map: profile_id -> probe_name -> expectation record.
    """

    profiles = matrix.get("profiles") or {}
    idx: Dict[str, Dict[str, Any]] = {}
    for profile_id, rec in profiles.items():
        probes = rec.get("probes") or []
        by_name: Dict[str, Any] = {}
        for probe in probes:
            name = probe.get("name")
            if not name:
                continue
            by_name[name] = probe
        idx[profile_id] = by_name
    return idx


def _expectation_for(
    expectations_index: Mapping[str, Mapping[str, Any]],
    profile_id: str,
    probe_name: Optional[str],
) -> Dict[str, Any]:
    return (expectations_index.get(profile_id) or {}).get(probe_name or "", {}) or {}


def normalize_runtime_results(
    expected_matrix: Mapping[str, Any],
    runtime_results: Mapping[str, Any],
    world_id: Optional[str] = None,
    harness_version: Optional[str] = None,
) -> List[RuntimeObservation]:
    """
    Normalize harness output into RuntimeObservation rows.

    expected_matrix: full parsed expected_matrix.json.
    runtime_results: full parsed runtime_results.json.
    world_id: overrides the world id to stamp on observations (defaults to WORLD_ID).
    harness_version: optional string to tag the harness build/revision.
    """

    resolved_world = world_id or expected_matrix.get("world_id") or runtime_results.get("world_id") or WORLD_ID
    expectations_idx = _index_expectations(expected_matrix or {})

    observations: List[RuntimeObservation] = []
    for profile_id, profile_result in (runtime_results or {}).items():
        probes = profile_result.get("probes") or []
        for probe in probes:
            probe_name = probe.get("name")
            expectation_rec = _expectation_for(expectations_idx, profile_id, probe_name)
            op = probe.get("operation") or expectation_rec.get("operation")
            target = probe.get("path") or probe.get("target") or expectation_rec.get("target")
            expectation_id = probe.get("expectation_id") or expectation_rec.get("expectation_id")
            expectation_id = expectation_id or derive_expectation_id(profile_id, op, target)
            scenario_id = make_scenario_id(
                resolved_world,
                profile_id,
                probe_name=probe_name or expectation_rec.get("name"),
                expectation_id=expectation_id,
                operation=op,
                target=target,
            )
            expected_decision = probe.get("expected") or expectation_rec.get("expected")
            actual_decision = probe.get("actual")
            match = probe.get("match")
            runtime_result = probe.get("runtime_result") or {}

            stderr_raw = probe.get("stderr")
            apply_report = runtime_result.get("apply_report")
            if apply_report is None and stderr_raw:
                for line in stderr_raw.splitlines():
                    candidate = line.strip()
                    if not (candidate.startswith("{") and candidate.endswith("}")):
                        continue
                    try:
                        payload = json.loads(candidate)
                    except json.JSONDecodeError:
                        continue
                    if payload.get("tool") != "sbpl-apply" or payload.get("stage") != "apply":
                        continue
                    apply_report = {
                        "api": payload.get("api"),
                        "rc": payload.get("rc"),
                        "errno": payload.get("errno"),
                        "errbuf": payload.get("errbuf"),
                    }
                    break

            observations.append(
                RuntimeObservation(
                    world_id=resolved_world,
                    profile_id=profile_id,
                    scenario_id=scenario_id,
                    expectation_id=expectation_id,
                    operation=op or "",
                    target=target,
                    probe_name=probe_name or expectation_rec.get("name"),
                    expected=expected_decision,
                    actual=actual_decision,
                    match=match,
                    runtime_status=runtime_result.get("status"),
                    errno=runtime_result.get("errno"),
                    errno_name=None,
                    failure_stage=runtime_result.get("failure_stage"),
                    failure_kind=runtime_result.get("failure_kind"),
                    apply_report=apply_report,
                    violation_summary=probe.get("violation_summary"),
                    command=probe.get("command"),
                    stdout=probe.get("stdout"),
                    stderr=_strip_sbpl_apply_markers(stderr_raw),
                    harness=harness_version,
                    notes=probe.get("notes"),
                )
            )
    return observations


def load_json(path: Path | str) -> Any:
    """
    Read a JSON file with repo-relative resolution.
    """

    abs_path = path_utils.ensure_absolute(Path(path), path_utils.find_repo_root(Path(__file__)))
    with abs_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_observations(observations: Iterable[RuntimeObservation], out_path: Path | str) -> Path:
    """
    Write observations as a JSON array to the given path.
    """

    path = path_utils.ensure_absolute(Path(out_path), path_utils.find_repo_root(Path(__file__)))
    payload = [serialize_observation(o) for o in observations]
    path.parent.mkdir(parents=True, exist_ok=True)
    import json

    path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return path


def normalize_from_paths(
    expected_matrix_path: Path | str,
    runtime_results_path: Path | str,
    world_id: Optional[str] = None,
    harness_version: Optional[str] = None,
) -> List[RuntimeObservation]:
    """
    Load expected_matrix + runtime_results from disk and return normalized observations.
    """

    expected_doc = load_json(expected_matrix_path)
    runtime_doc = load_json(runtime_results_path)
    return normalize_runtime_results(expected_doc, runtime_doc, world_id=world_id, harness_version=harness_version)


def write_normalized_events(
    expected_matrix_path: Path | str,
    runtime_results_path: Path | str,
    out_path: Path | str,
    world_id: Optional[str] = None,
    harness_version: Optional[str] = None,
) -> Path:
    """
    Normalize events from disk and write them as a JSON array.
    """

    observations = normalize_from_paths(expected_matrix_path, runtime_results_path, world_id=world_id, harness_version=harness_version)
    return write_observations(observations, out_path)
