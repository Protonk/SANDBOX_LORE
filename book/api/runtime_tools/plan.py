"""
Plan-data loader and compiler for runtime tools.

Plans reference registry profile/probe descriptors and are compiled into
ProfileSpec entries for the shared harness runner.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from book.api import path_utils
from book.api.runtime_tools import workflow
from book.api.runtime_tools.registry import load_registry, resolve_probe, resolve_profile


REPO_ROOT = path_utils.find_repo_root(Path(__file__))
PLAN_SCHEMA_VERSION = "runtime-tools.plan.v0.1"


@dataclass(frozen=True)
class PlanSpec:
    plan_id: str
    world_id: Optional[str]
    registry_id: str
    profiles: Sequence[str]
    lanes: Dict[str, bool]
    controls: Dict[str, Any]
    schema_versions: Dict[str, str]
    apply_preflight_profile: Optional[str]
    notes: Optional[str]


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())


def load_plan(path: Path) -> Dict[str, Any]:
    plan_path = path_utils.ensure_absolute(path, REPO_ROOT)
    doc = _load_json(plan_path)
    if doc.get("schema_version") != PLAN_SCHEMA_VERSION:
        raise ValueError(f"plan schema mismatch: {doc.get('schema_version')}")
    if not doc.get("plan_id"):
        raise ValueError("plan_id missing")
    if not doc.get("registry_id"):
        raise ValueError("registry_id missing")
    if not isinstance(doc.get("profiles"), list):
        raise ValueError("profiles must be a list")
    return doc


def plan_digest(doc: Dict[str, Any]) -> str:
    payload = {
        "plan_id": doc.get("plan_id"),
        "registry_id": doc.get("registry_id"),
        "profiles": doc.get("profiles") or [],
        "lanes": doc.get("lanes") or {},
        "controls": doc.get("controls") or {},
        "schema_versions": doc.get("schema_versions") or {},
        "apply_preflight_profile": doc.get("apply_preflight_profile"),
    }
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _probe_to_row(probe: Dict[str, Any], profile_id: str) -> Dict[str, Any]:
    name = probe.get("name")
    operation = probe.get("operation")
    target = probe.get("target")
    expected = probe.get("expected")
    expectation_id = probe.get("expectation_id") or probe.get("probe_id")
    if not expectation_id:
        expectation_id = f"{profile_id}:{name or operation or 'probe'}"
    row = {
        "name": name,
        "operation": operation,
        "target": target,
        "expected": expected,
        "expectation_id": expectation_id,
    }
    if probe.get("mode"):
        row["mode"] = probe.get("mode")
    if probe.get("driver"):
        row["driver"] = probe.get("driver")
    return row


def compile_profiles(
    plan_doc: Dict[str, Any],
    *,
    only_profiles: Optional[Iterable[str]] = None,
    only_scenarios: Optional[Iterable[str]] = None,
) -> List[workflow.ProfileSpec]:
    registry_id = plan_doc["registry_id"]
    try:
        registry = load_registry(registry_id)
    except Exception as exc:
        errors.append(f"registry load failed: {registry_id}: {exc}")
        return doc, errors
    only_profiles_set = set(only_profiles or [])
    only_scenarios_set = set(only_scenarios or [])
    profiles: List[workflow.ProfileSpec] = []
    for profile_id in plan_doc.get("profiles") or []:
        if only_profiles_set and profile_id not in only_profiles_set:
            continue
        profile = resolve_profile(registry_id, profile_id)
        probe_rows = []
        for probe_ref in profile.get("probe_refs") or []:
            probe = resolve_probe(registry_id, probe_ref)
            row = _probe_to_row(probe, profile_id)
            if only_scenarios_set and row.get("expectation_id") not in only_scenarios_set:
                continue
            probe_rows.append(row)
        if not probe_rows:
            continue
        profile_path = path_utils.ensure_absolute(Path(profile["profile_path"]), REPO_ROOT)
        profiles.append(
            workflow.ProfileSpec(
                profile_id=profile_id,
                profile_path=profile_path,
                probes=probe_rows,
                mode=profile.get("mode"),
                family=profile.get("family"),
                semantic_group=profile.get("semantic_group"),
                key_specific_rules=profile.get("key_specific_rules") or [],
            )
        )
    return profiles


def list_plan_paths(root: Optional[Path] = None) -> List[Path]:
    repo_root = path_utils.ensure_absolute(root or REPO_ROOT, REPO_ROOT)
    experiments_root = repo_root / "book" / "experiments"
    if not experiments_root.exists():
        return []
    return sorted(experiments_root.rglob("plan.json"))


def list_plans(root: Optional[Path] = None) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    for path in list_plan_paths(root=root):
        try:
            doc = load_plan(path)
        except Exception as exc:
            entries.append(
                {
                    "path": str(path_utils.to_repo_relative(path, repo_root=REPO_ROOT)),
                    "error": str(exc),
                }
            )
            continue
        entries.append(
            {
                "plan_id": doc.get("plan_id"),
                "registry_id": doc.get("registry_id"),
                "profiles": len(doc.get("profiles") or []),
                "path": str(path_utils.to_repo_relative(path, repo_root=REPO_ROOT)),
            }
        )
    return entries


def lint_plan(path: Path) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    errors: List[str] = []
    try:
        doc = load_plan(path)
    except Exception as exc:
        return None, [str(exc)]

    registry_id = doc.get("registry_id")
    if not registry_id:
        errors.append("missing registry_id")
        return doc, errors

    profiles = doc.get("profiles") or []
    if not profiles:
        errors.append("profiles list is empty")
        return doc, errors

    registry = load_registry(registry_id)
    probes = registry.get("probes") or {}
    for profile_id in profiles:
        try:
            profile = resolve_profile(registry_id, profile_id)
        except KeyError:
            errors.append(f"unknown profile: {registry_id}:{profile_id}")
            continue
        profile_path = profile.get("profile_path")
        if not profile_path:
            errors.append(f"profile missing profile_path: {registry_id}:{profile_id}")
        else:
            abs_path = path_utils.ensure_absolute(Path(profile_path), REPO_ROOT)
            if not abs_path.exists():
                errors.append(f"profile_path missing: {registry_id}:{profile_id} -> {profile_path}")
        probe_refs = profile.get("probe_refs") or []
        if not probe_refs:
            errors.append(f"profile has no probe_refs: {registry_id}:{profile_id}")
        for probe_ref in probe_refs:
            if probe_ref not in probes:
                errors.append(f"unknown probe_ref: {registry_id}:{profile_id}:{probe_ref}")

    apply_preflight_profile = doc.get("apply_preflight_profile")
    if apply_preflight_profile:
        abs_path = path_utils.ensure_absolute(Path(apply_preflight_profile), REPO_ROOT)
        if not abs_path.exists():
            errors.append(f"apply_preflight_profile missing: {apply_preflight_profile}")

    return doc, errors
