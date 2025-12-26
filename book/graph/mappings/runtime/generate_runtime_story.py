#!/usr/bin/env python3
"""
Generate a joined per-op runtime story from the latest runtime cut.

Reads the canonical op/scenario mappings from book/graph/mappings/runtime_cuts/
and emits runtime_story.json alongside them. Updates runtime_manifest.json to
include a pointer to the story file so loaders can discover it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from book.api import path_utils
from book.api.runtime_tools.mapping import story as rt_story

CUT_ROOT = ROOT / "book" / "graph" / "mappings" / "runtime_cuts"
ADV_RUNTIME_OPS = ROOT / "book" / "experiments" / "runtime-adversarial" / "out" / "runtime_mappings" / "ops.json"
ADV_RUNTIME_SCENARIOS = ROOT / "book" / "experiments" / "runtime-adversarial" / "out" / "runtime_mappings" / "scenarios.json"
RUN_MANIFEST_CHECKS = ROOT / "book" / "experiments" / "runtime-checks" / "out" / "run_manifest.json"
RUN_MANIFEST_ADV = ROOT / "book" / "experiments" / "runtime-adversarial" / "out" / "run_manifest.json"


def sha256_path(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def load_run_manifest(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def require_clean_manifest(manifest: dict, label: str) -> None:
    channel = manifest.get("channel")
    if channel != "launchd_clean":
        raise RuntimeError(f"{label} run manifest is not clean: channel={channel!r}")


def merge_story(base_doc: dict, extra_doc: dict) -> bool:
    base_ops = base_doc.get("ops")
    extra_ops = extra_doc.get("ops")
    if not isinstance(base_ops, dict) or not isinstance(extra_ops, dict):
        return False
    merged = False
    for key, extra_entry in extra_ops.items():
        if key not in base_ops:
            base_ops[key] = extra_entry
            merged = True
            continue
        base_entry = base_ops.get(key) or {}
        base_scenarios = base_entry.get("scenarios") or []
        extra_scenarios = extra_entry.get("scenarios") or []
        if not extra_scenarios:
            continue
        seen = {s.get("scenario_id") for s in base_scenarios if isinstance(s, dict)}
        appended = [s for s in extra_scenarios if isinstance(s, dict) and s.get("scenario_id") not in seen]
        if appended:
            base_entry["scenarios"] = list(base_scenarios) + appended
            base_ops[key] = base_entry
            merged = True
    base_doc["ops"] = base_ops
    return merged


def main() -> None:
    manifest_path = CUT_ROOT / "runtime_manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"missing runtime manifest at {manifest_path}; run promotion first")

    manifest = json.loads(manifest_path.read_text())
    scenarios_path = path_utils.ensure_absolute(manifest.get("scenarios"), ROOT)
    ops_path = path_utils.ensure_absolute(manifest.get("ops"), ROOT)
    run_manifest_checks = load_run_manifest(RUN_MANIFEST_CHECKS)
    if not run_manifest_checks:
        raise RuntimeError("missing runtime-checks run_manifest.json; run via launchctl clean channel")
    require_clean_manifest(run_manifest_checks, "runtime-checks")
    run_manifest_adv = load_run_manifest(RUN_MANIFEST_ADV)

    story = rt_story.build_story(ops_path, scenarios_path)
    inputs = [
        path_utils.to_repo_relative(ops_path, ROOT),
        path_utils.to_repo_relative(scenarios_path, ROOT),
    ]
    input_hashes = {
        inputs[0]: sha256_path(ops_path),
        inputs[1]: sha256_path(scenarios_path),
    }
    if ADV_RUNTIME_OPS.exists() and ADV_RUNTIME_SCENARIOS.exists():
        if not run_manifest_adv:
            raise RuntimeError("missing runtime-adversarial run_manifest.json; run via launchctl clean channel")
        require_clean_manifest(run_manifest_adv, "runtime-adversarial")
        adv_story = rt_story.build_story(ADV_RUNTIME_OPS, ADV_RUNTIME_SCENARIOS)
        if merge_story(story, adv_story):
            inputs.extend(
                [
                    path_utils.to_repo_relative(ADV_RUNTIME_OPS, ROOT),
                    path_utils.to_repo_relative(ADV_RUNTIME_SCENARIOS, ROOT),
                ]
            )
            input_hashes[path_utils.to_repo_relative(ADV_RUNTIME_OPS, ROOT)] = sha256_path(ADV_RUNTIME_OPS)
            input_hashes[path_utils.to_repo_relative(ADV_RUNTIME_SCENARIOS, ROOT)] = sha256_path(ADV_RUNTIME_SCENARIOS)
    run_manifest_inputs = []
    run_ids = []
    repo_root_contexts = []
    if run_manifest_checks:
        run_manifest_inputs.append(path_utils.to_repo_relative(RUN_MANIFEST_CHECKS, ROOT))
        if run_manifest_checks.get("run_id"):
            run_ids.append(run_manifest_checks.get("run_id"))
        if run_manifest_checks.get("repo_root_context"):
            repo_root_contexts.append(run_manifest_checks.get("repo_root_context"))
    if run_manifest_adv:
        run_manifest_inputs.append(path_utils.to_repo_relative(RUN_MANIFEST_ADV, ROOT))
        if run_manifest_adv.get("run_id"):
            run_ids.append(run_manifest_adv.get("run_id"))
        if run_manifest_adv.get("repo_root_context"):
            repo_root_contexts.append(run_manifest_adv.get("repo_root_context"))
    if run_manifest_inputs:
        inputs.extend(run_manifest_inputs)
        for rel in run_manifest_inputs:
            input_hashes[rel] = sha256_path(path_utils.ensure_absolute(Path(rel), ROOT))
    meta = story.get("meta", {})
    meta["inputs"] = inputs
    meta["input_hashes"] = input_hashes
    meta["run_provenance"] = {
        "run_ids": run_ids,
        "manifests": run_manifest_inputs,
        "repo_root_contexts": repo_root_contexts,
    }
    manifest_meta = manifest.get("meta") or {}
    if manifest_meta.get("source_jobs"):
        meta["source_jobs"] = manifest_meta["source_jobs"]
    if ADV_RUNTIME_OPS.exists() and ADV_RUNTIME_SCENARIOS.exists():
        note = meta.get("notes") or ""
        if "runtime-adversarial" not in note:
            meta["notes"] = (note + " " if note else "") + "Includes runtime-adversarial runtime_mappings."
    story["meta"] = meta
    out_path = CUT_ROOT / "runtime_story.json"
    rt_story.write_story(story, out_path)

    manifest["runtime_story"] = path_utils.to_repo_relative(out_path, ROOT)
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"[+] wrote runtime story to {out_path}")


if __name__ == "__main__":
    main()
