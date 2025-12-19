"""
Validation job for the gate-witnesses experiment.

This job re-runs the checked-in minimized witness pairs and asserts that they
still witness the intended boundary on this world:

- minimal failing: apply-stage EPERM (profile did not attach)
- passing neighbor: failure_stage != "apply" (not apply-gated)

If sandbox_init is globally gated in the current execution environment (e.g.,
inside a harness sandbox), this job reports status=blocked.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from book.api.path_utils import find_repo_root, to_repo_relative
from book.api.runtime import contract as rt_contract
from book.api.runtime import events as runtime_events
from book.graph.concepts.validation import registry
from book.graph.concepts.validation.registry import ValidationJob

ROOT = find_repo_root(Path(__file__))
WITNESS_ROOT = ROOT / "book/experiments/gate-witnesses/out/witnesses"
OUT_DIR = ROOT / "book/graph/concepts/validation/out/experiments/gate-witnesses"
STATUS_PATH = OUT_DIR / "status.json"
RESULTS_PATH = OUT_DIR / "witness_results.json"

WRAPPER = ROOT / "book/api/SBPL-wrapper/wrapper"
CONTROL_SBPL = ROOT / "book/experiments/op-table-operation/sb/v0_empty.sb"

EPERM = 1

CLEAR_LOG_ENV = "SANDBOX_LORE_CAPTURE_UNIFIED_LOG"
DEFAULT_LOG_WINDOW_SECONDS = 8


def rel(path: Path) -> str:
    return to_repo_relative(path, ROOT)


def _run_wrapper(sbpl_path: Path, timeout_sec: int = 5) -> Dict[str, Any]:
    cmd_exec = [str(WRAPPER), "--sbpl", str(sbpl_path), "--", "/usr/bin/true"]
    cmd = [rel(WRAPPER), "--sbpl", rel(sbpl_path), "--", "/usr/bin/true"]
    proc = subprocess.run(cmd_exec, capture_output=True, text=True, timeout=timeout_sec)
    stderr_raw = proc.stderr or ""
    upgraded = rt_contract.upgrade_runtime_result({}, stderr_raw)
    return {
        "cmd": cmd,
        "wrapper_rc": proc.returncode,
        "failure_stage": upgraded.get("failure_stage") if isinstance(upgraded.get("failure_stage"), str) else None,
        "failure_kind": upgraded.get("failure_kind") if isinstance(upgraded.get("failure_kind"), str) else None,
        "apply_report": upgraded.get("apply_report") if isinstance(upgraded.get("apply_report"), dict) else None,
        "stderr": rt_contract.strip_tool_markers(stderr_raw) or "",
    }


def _run_wrapper_compile(sbpl_path: Path, out_blob: Path, timeout_sec: int = 10) -> Dict[str, Any]:
    cmd_exec = [str(WRAPPER), "--compile", str(sbpl_path), "--out", str(out_blob)]
    cmd = [rel(WRAPPER), "--compile", rel(sbpl_path), "--out", rel(out_blob)]
    proc = subprocess.run(cmd_exec, capture_output=True, text=True, timeout=timeout_sec)
    stderr_raw = proc.stderr or ""
    markers = rt_contract.extract_sbpl_compile_markers(stderr_raw)
    marker = markers[0] if markers else None
    marker_fields = {
        "marker_schema_version": marker.get("marker_schema_version") if isinstance(marker, dict) else None,
        "rc": marker.get("rc") if isinstance(marker, dict) else None,
        "errno": marker.get("errno") if isinstance(marker, dict) else None,
        "errbuf": marker.get("errbuf") if isinstance(marker, dict) else None,
        "profile_type": marker.get("profile_type") if isinstance(marker, dict) else None,
        "bytecode_length": marker.get("bytecode_length") if isinstance(marker, dict) else None,
    }
    return {
        "cmd": cmd,
        "wrapper_rc": proc.returncode,
        "marker": marker_fields,
        "marker_count": len(markers),
        "stderr": rt_contract.strip_tool_markers(stderr_raw) or "",
    }


def _run_wrapper_blob(blob_path: Path, timeout_sec: int = 5) -> Dict[str, Any]:
    cmd_exec = [str(WRAPPER), "--blob", str(blob_path), "--", "/usr/bin/true"]
    cmd = [rel(WRAPPER), "--blob", rel(blob_path), "--", "/usr/bin/true"]
    proc = subprocess.run(cmd_exec, capture_output=True, text=True, timeout=timeout_sec)
    stderr_raw = proc.stderr or ""
    upgraded = rt_contract.upgrade_runtime_result({}, stderr_raw)
    return {
        "cmd": cmd,
        "wrapper_rc": proc.returncode,
        "failure_stage": upgraded.get("failure_stage") if isinstance(upgraded.get("failure_stage"), str) else None,
        "failure_kind": upgraded.get("failure_kind") if isinstance(upgraded.get("failure_kind"), str) else None,
        "apply_report": upgraded.get("apply_report") if isinstance(upgraded.get("apply_report"), dict) else None,
        "stderr": rt_contract.strip_tool_markers(stderr_raw) or "",
    }


def _capture_unified_log(out_path: Path, last_seconds: int) -> Dict[str, Any]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    predicate = (
        '(eventMessage CONTAINS[c] "message filter") OR (eventMessage CONTAINS[c] "message-filter") OR '
        '(eventMessage CONTAINS[c] "sandbox")'
    )
    cmd = [
        "/usr/bin/log",
        "show",
        "--style",
        "syslog",
        "--last",
        f"{last_seconds}s",
        "--predicate",
        predicate,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    (out_path).write_text(proc.stdout or "")
    return {
        "cmd": cmd,
        "rc": proc.returncode,
        "out_path": rel(out_path),
        "predicate": predicate,
        "last_seconds": last_seconds,
        "stderr": (proc.stderr or "").strip() or None,
        "stdout_bytes": len(proc.stdout.encode("utf-8")) if proc.stdout else 0,
    }


def _is_apply_gate_eperm(result: Dict[str, Any]) -> bool:
    if result.get("failure_stage") != "apply":
        return False
    report = result.get("apply_report")
    if not isinstance(report, dict):
        return False
    return report.get("errno") == EPERM


def _is_not_apply_gate(result: Dict[str, Any]) -> bool:
    return result.get("failure_stage") != "apply"


def run_gate_witnesses_job() -> Dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    capture_unified_log = bool(os.environ.get(CLEAR_LOG_ENV))

    if not WITNESS_ROOT.exists():
        raise FileNotFoundError(f"missing witness root: {WITNESS_ROOT}")
    if not WRAPPER.exists():
        raise FileNotFoundError(f"missing wrapper binary: {WRAPPER}")

    # Environment sanity: if sandbox_init is globally gated here, witnesses are not meaningful.
    control = _run_wrapper(CONTROL_SBPL)
    if _is_apply_gate_eperm(control):
        payload = {
            "job_id": "experiment:gate-witnesses",
            "status": "blocked",
            "host": {},
            "inputs": [rel(CONTROL_SBPL)],
            "outputs": [rel(RESULTS_PATH), rel(STATUS_PATH)],
            "notes": "sandbox_init appears globally apply-gated in this execution context (control profile failed apply-stage EPERM); rerun outside the harness sandbox.",
            "metrics": {"witnesses": 0},
        }
        RESULTS_PATH.write_text(
            json.dumps(
                {
                    "world_id": runtime_events.WORLD_ID,
                    "control": control,
                    "witnesses": [],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return {
            "status": "blocked",
            "inputs": payload["inputs"],
            "outputs": payload["outputs"],
            "metrics": payload["metrics"],
            "notes": payload["notes"],
        }

    results: List[Dict[str, Any]] = []
    failures: List[str] = []

    for dirpath in sorted(p for p in WITNESS_ROOT.iterdir() if p.is_dir()):
        failing_path = dirpath / "minimal_failing.sb"
        neighbor_path = dirpath / "passing_neighbor.sb"
        if not failing_path.exists() or not neighbor_path.exists():
            continue

        failing = _run_wrapper(failing_path)
        neighbor = _run_wrapper(neighbor_path)

        forensics: Optional[Dict[str, Any]] = None
        if capture_unified_log:
            forensics_dir = OUT_DIR / "forensics" / dirpath.name
            blob_path = forensics_dir / "minimal_failing.sb.bin"
            compile_result = _run_wrapper_compile(failing_path, blob_path)
            blob_result: Optional[Dict[str, Any]] = None
            if blob_path.exists():
                blob_result = _run_wrapper_blob(blob_path)
            log_path = forensics_dir / "log_show_last.txt"
            log_result = _capture_unified_log(log_path, DEFAULT_LOG_WINDOW_SECONDS)
            forensics = {
                "capture_unified_log": True,
                "compile": compile_result,
                "blob_apply": blob_result,
                "unified_log": log_result,
            }

        ok = _is_apply_gate_eperm(failing) and _is_not_apply_gate(neighbor)
        if not ok:
            failures.append(dirpath.name)

        results.append(
            {
                "target": dirpath.name,
                "minimal_failing": {"path": rel(failing_path), "result": failing},
                "passing_neighbor": {"path": rel(neighbor_path), "result": neighbor},
                "forensics": forensics,
                "ok": ok,
            }
        )

    RESULTS_PATH.write_text(
        json.dumps(
            {
                "world_id": runtime_events.WORLD_ID,
                "control": control,
                "witnesses": results,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    status = "ok" if not failures else "partial"
    notes: Optional[str] = None
    if failures:
        notes = f"witness predicate failed for: {', '.join(failures)}"

    payload = {
        "job_id": "experiment:gate-witnesses",
        "status": status,
        "host": {},
        "inputs": [rel(WITNESS_ROOT)],
        "outputs": [rel(RESULTS_PATH), rel(STATUS_PATH)],
        "metrics": {"witnesses": len(results), "failures": len(failures)},
        "notes": notes or "Verified apply-gate witness pairs via SBPL-wrapper and runtime contract classification.",
        "tags": ["experiment:gate-witnesses", "experiment", "apply-gate"],
    }
    STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    return {
        "status": status,
        "inputs": payload["inputs"],
        "outputs": payload["outputs"],
        "metrics": payload["metrics"],
        "notes": payload["notes"],
        "host": payload["host"],
    }


registry.register(
    ValidationJob(
        id="experiment:gate-witnesses",
        inputs=[rel(WITNESS_ROOT)],
        outputs=[rel(RESULTS_PATH), rel(STATUS_PATH)],
        tags=["experiment:gate-witnesses", "experiment", "apply-gate"],
        description="Re-run minimized apply-gate witnesses and assert they still witness apply-stage EPERM boundaries on this world.",
        example_command="python -m book.graph.concepts.validation --experiment gate-witnesses",
        runner=run_gate_witnesses_job,
    )
)
