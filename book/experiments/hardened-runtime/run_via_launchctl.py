#!/usr/bin/env python3
"""
Launch hardened-runtime via launchctl to avoid inheriting a sandboxed parent.

This runner bootstraps a transient LaunchAgent that executes run_hardened_runtime.py
with --require-clean. The job aborts if apply preflight fails.
"""
from __future__ import annotations

import argparse
import json
import os
import plistlib
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book.api import path_utils

LAUNCHCTL = Path("/bin/launchctl")
PYTHON = Path("/usr/bin/python3")
RUNNER = Path(__file__).with_name("run_hardened_runtime.py")
OUT_ROOT = Path(__file__).with_name("out")
LAUNCHCTL_DIR = OUT_ROOT / "launchctl"
STAGING_BASE = Path("/private/tmp/sandbox-lore-launchctl")
BASELINE = REPO_ROOT / "book" / "world" / "sonoma-14.4.1-23E224-arm64" / "world-baseline.json"

RUN_MANIFEST_SCHEMA_VERSION = "hardened-runtime.run_manifest.v0.2"
ARTIFACT_INDEX_SCHEMA_VERSION = "hardened-runtime.artifact_index.v0.1"

ARTIFACTS = [
    "apply_preflight.json",
    "baseline_results.json",
    "runtime_results.json",
    "runtime_events.normalized.json",
    "expected_matrix.generated.json",
    "expected_matrix.json",
    "mismatch_summary.json",
    "mismatch_packets.jsonl",
    "oracle_results.json",
    "summary.json",
    "summary.md",
]


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def build_plist(
    label: str,
    stdout_path: Path,
    stderr_path: Path,
    require_clean: bool,
    seatbelt_callout: bool,
    repo_root: Path,
    runner_path: Path,
    run_id: str,
) -> Dict[str, Any]:
    program = str(PYTHON if PYTHON.exists() else sys.executable)
    args = [program, str(runner_path)]
    if not require_clean:
        args.append("--no-require-clean")
    env = {
        "PYTHONPATH": str(repo_root),
        "SANDBOX_LORE_RUN_ID": run_id,
        "SANDBOX_LORE_LAUNCHD_CLEAN": "1" if require_clean else "0",
    }
    if seatbelt_callout:
        env["SANDBOX_LORE_SEATBELT_CALLOUT"] = "1"
    return {
        "Label": label,
        "ProgramArguments": args,
        "RunAtLoad": True,
        "WorkingDirectory": str(repo_root),
        "StandardOutPath": str(stdout_path),
        "StandardErrorPath": str(stderr_path),
        "EnvironmentVariables": env,
    }


def wait_for_output(stdout_path: Path, stderr_path: Path, timeout: float) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        if stdout_path.exists() and stdout_path.stat().st_size > 0:
            return True
        if stderr_path.exists() and stderr_path.stat().st_size > 0:
            return True
        time.sleep(0.5)
    return False


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _sha256_path(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _git_commit(repo_root: Path) -> str | None:
    try:
        res = subprocess.run(["/usr/bin/git", "rev-parse", "HEAD"], cwd=repo_root, capture_output=True, text=True)
        if res.returncode != 0:
            return None
        return res.stdout.strip() or None
    except Exception:
        return None


def _load_schema_version(path: Path) -> str | None:
    if not path.exists():
        return None
    if path.suffix == ".jsonl":
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                return None
            return row.get("schema_version")
        return None
    if path.suffix == ".json":
        try:
            doc = json.loads(path.read_text())
        except Exception:
            return None
        if isinstance(doc, dict):
            return doc.get("schema_version")
    return None


def load_baseline() -> Dict[str, Any]:
    return load_json(BASELINE)


def build_run_manifest(
    *,
    run_id: str,
    label: str,
    repo_root: Path,
    stage_used: bool,
    stage_root: Path | None,
    job_out_dir: Path,
    out_root: Path,
    require_clean: bool,
    seatbelt_callout: bool,
    stdout_rel: str | None,
    stderr_rel: str | None,
) -> Dict[str, Any]:
    apply_preflight_path = out_root / "apply_preflight.json"
    apply_preflight = load_json(apply_preflight_path)
    baseline = load_baseline()
    world_id = apply_preflight.get("world_id") or baseline.get("world_id")
    apply_ok = apply_preflight.get("apply_ok") if apply_preflight else None
    channel = "launchd_clean" if require_clean and apply_ok else "launchd_unclean"
    return {
        "schema_version": RUN_MANIFEST_SCHEMA_VERSION,
        "run_id": run_id,
        "world_id": world_id,
        "baseline_ref": path_utils.to_repo_relative(BASELINE, repo_root=repo_root) if BASELINE.exists() else None,
        "host": baseline.get("host") if isinstance(baseline.get("host"), dict) else None,
        "channel": channel,
        "label": label,
        "runner": path_utils.to_repo_relative(RUNNER, repo_root=repo_root),
        "stage_used": stage_used,
        "stage_root": str(stage_root) if stage_root else None,
        "repo_root_context": str(stage_root) if stage_used and stage_root else str(repo_root),
        "staged_output_root": str(job_out_dir) if stage_used else None,
        "output_root": path_utils.to_repo_relative(out_root, repo_root=repo_root),
        "stdout": stdout_rel,
        "stderr": stderr_rel,
        "seatbelt_callout": seatbelt_callout,
        "apply_preflight": {
            "path": path_utils.to_repo_relative(apply_preflight_path, repo_root=repo_root)
            if apply_preflight_path.exists()
            else None,
            "record": apply_preflight or None,
        },
        "sandbox_check_self": (apply_preflight.get("sandbox_check_self") if apply_preflight else None),
        "fingerprint": (apply_preflight.get("fingerprint") if apply_preflight else None),
    }


def build_artifact_index(
    *,
    out_root: Path,
    run_manifest: Dict[str, Any],
    repo_root: Path,
) -> Dict[str, Any]:
    run_id = run_manifest.get("run_id")
    world_id = run_manifest.get("world_id")
    artifacts = []
    missing = []
    for name in ARTIFACTS + ["run_manifest.json"]:
        path = out_root / name
        if not path.exists():
            missing.append(path_utils.to_repo_relative(path, repo_root=repo_root))
            continue
        artifacts.append(
            {
                "path": path_utils.to_repo_relative(path, repo_root=repo_root),
                "file_size": path.stat().st_size,
                "sha256": _sha256_path(path),
                "schema_version": _load_schema_version(path),
            }
        )
    producer = {
        "git_commit": _git_commit(repo_root),
        "python": sys.version.split()[0],
        "runner": path_utils.to_repo_relative(RUNNER, repo_root=repo_root),
        "runner_sha256": _sha256_path(RUNNER) if RUNNER.exists() else None,
        "launchctl_runner": path_utils.to_repo_relative(Path(__file__), repo_root=repo_root),
        "launchctl_runner_sha256": _sha256_path(Path(__file__)),
        "sandbox_runner": path_utils.to_repo_relative(
            REPO_ROOT / "book" / "experiments" / "runtime-checks" / "sandbox_runner",
            repo_root=repo_root,
        ),
        "sandbox_runner_sha256": _sha256_path(REPO_ROOT / "book" / "experiments" / "runtime-checks" / "sandbox_runner")
        if (REPO_ROOT / "book" / "experiments" / "runtime-checks" / "sandbox_runner").exists()
        else None,
    }
    try:
        from book.api.runtime_tools.core import contract as rt_contract  # type: ignore

        producer["tool_versions"] = {
            "runtime_result_schema_version": rt_contract.CURRENT_RUNTIME_RESULT_SCHEMA_VERSION,
            "tool_marker_schema_version": rt_contract.CURRENT_TOOL_MARKER_SCHEMA_VERSION,
            "seatbelt_callout_schema_version": rt_contract.CURRENT_SEATBELT_CALLOUT_MARKER_SCHEMA_VERSION,
            "entitlement_check_schema_version": rt_contract.CURRENT_ENTITLEMENT_CHECK_MARKER_SCHEMA_VERSION,
        }
    except Exception:
        producer["tool_versions"] = None
    return {
        "schema_version": ARTIFACT_INDEX_SCHEMA_VERSION,
        "run_id": run_id,
        "world_id": world_id,
        "artifacts": artifacts,
        "missing": missing,
        "producer": producer,
    }


def stage_repo(label: str) -> Path:
    stage_root = STAGING_BASE / label
    if stage_root.exists():
        shutil.rmtree(stage_root)
    stage_root.mkdir(parents=True, exist_ok=True)
    agents = REPO_ROOT / "AGENTS.md"
    if agents.exists():
        shutil.copy2(agents, stage_root / "AGENTS.md")
    shutil.copytree(
        REPO_ROOT / "book",
        stage_root / "book",
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"),
    )
    return stage_root


def sync_outputs(
    staged_out: Path,
    dest_out: Path,
    stdout_path: Path,
    stderr_path: Path,
    repo_root: Path,
) -> Dict[str, str]:
    sync: Dict[str, str] = {}
    if staged_out.exists():
        shutil.copytree(
            staged_out,
            dest_out,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("launchctl"),
        )
    dest_launchctl = dest_out / "launchctl"
    dest_launchctl.mkdir(parents=True, exist_ok=True)
    if stdout_path.exists():
        dest_stdout = dest_launchctl / stdout_path.name
        shutil.copy2(stdout_path, dest_stdout)
        sync["stdout"] = path_utils.to_repo_relative(dest_stdout, repo_root)
    if stderr_path.exists():
        dest_stderr = dest_launchctl / stderr_path.name
        shutil.copy2(stderr_path, dest_stderr)
        sync["stderr"] = path_utils.to_repo_relative(dest_stderr, repo_root)
    return sync


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run hardened-runtime via launchctl")
    parser.add_argument("--label", help="launchctl label override")
    parser.add_argument("--timeout", type=float, default=10.0, help="wait for output (seconds)")
    parser.add_argument("--keep-job", action="store_true", help="keep job loaded after run")
    parser.add_argument("--no-require-clean", action="store_true", help="allow run even if apply preflight fails")
    parser.add_argument("--no-seatbelt-callout", action="store_true", help="disable sandbox_check callouts")
    parser.add_argument("--no-stage", action="store_true", help="run from the repo root instead of staging to /private/tmp")
    parser.add_argument("--keep-stage", action="store_true", help="retain staged copy after run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not LAUNCHCTL.exists():
        print("[!] launchctl missing")
        return 2
    if not RUNNER.exists():
        print("[!] run_hardened_runtime.py missing")
        return 2

    label = args.label or f"sandbox-lore.hardened-runtime.{os.getpid()}"
    run_id = str(uuid.uuid4())
    stage_root: Path | None = None
    stage_used = not args.no_stage
    if stage_used:
        stage_root = stage_repo(label)
        repo_root = stage_root
        runner_path = stage_root / "book/experiments/hardened-runtime/run_hardened_runtime.py"
        job_out_dir = stage_root / "book/experiments/hardened-runtime/out"
    else:
        repo_root = REPO_ROOT
        runner_path = RUNNER
        job_out_dir = OUT_ROOT

    job_launchctl = job_out_dir / "launchctl"
    job_launchctl.mkdir(parents=True, exist_ok=True)
    stdout_path = job_launchctl / f"{label}.stdout.txt"
    stderr_path = job_launchctl / f"{label}.stderr.txt"
    plist_path = job_launchctl / f"{label}.plist"
    LAUNCHCTL_DIR.mkdir(parents=True, exist_ok=True)

    require_clean = not args.no_require_clean
    seatbelt_callout = not args.no_seatbelt_callout
    plist = build_plist(
        label,
        stdout_path,
        stderr_path,
        require_clean=require_clean,
        seatbelt_callout=seatbelt_callout,
        repo_root=repo_root,
        runner_path=runner_path,
        run_id=run_id,
    )
    plist_path.write_bytes(plistlib.dumps(plist))

    if stage_used:
        job_launchctl.mkdir(parents=True, exist_ok=True)
        staged_plist = job_launchctl / plist_path.name
        staged_plist.write_bytes(plistlib.dumps(plist))
        plist_path = staged_plist

    if stage_used:
        repo_out = REPO_ROOT / "book/experiments/hardened-runtime/out"
        repo_out.mkdir(parents=True, exist_ok=True)
    else:
        repo_out = OUT_ROOT

    for cmd in ([str(LAUNCHCTL), "bootout", "gui/" + str(os.getuid()), str(plist_path)] ,):
        try:
            subprocess.run(cmd, capture_output=True)
        except Exception:
            pass

    try:
        subprocess.run([str(LAUNCHCTL), "bootstrap", "gui/" + str(os.getuid()), str(plist_path)], check=True)
    except subprocess.CalledProcessError as exc:
        print(f"[!] launchctl bootstrap failed: {exc}")
        return 2

    wait_for_output(stdout_path, stderr_path, args.timeout)

    if not args.keep_job:
        subprocess.run([str(LAUNCHCTL), "bootout", "gui/" + str(os.getuid()), str(plist_path)], capture_output=True)

    stdout_rel = None
    stderr_rel = None
    if stage_used:
        synced = sync_outputs(job_out_dir, repo_out, stdout_path, stderr_path, REPO_ROOT)
        stdout_rel = synced.get("stdout")
        stderr_rel = synced.get("stderr")
    else:
        if stdout_path.exists():
            stdout_rel = path_utils.to_repo_relative(stdout_path, REPO_ROOT)
        if stderr_path.exists():
            stderr_rel = path_utils.to_repo_relative(stderr_path, REPO_ROOT)

    manifest = build_run_manifest(
        run_id=run_id,
        label=label,
        repo_root=REPO_ROOT,
        stage_used=stage_used,
        stage_root=stage_root,
        job_out_dir=job_out_dir,
        out_root=repo_out,
        require_clean=require_clean,
        seatbelt_callout=seatbelt_callout,
        stdout_rel=stdout_rel,
        stderr_rel=stderr_rel,
    )
    run_manifest_path = repo_out / "run_manifest.json"
    write_json(run_manifest_path, manifest)
    artifact_index = build_artifact_index(out_root=repo_out, run_manifest=manifest, repo_root=REPO_ROOT)
    artifact_index_path = repo_out / "artifact_index.json"
    write_json(artifact_index_path, artifact_index)
    manifest["artifact_index"] = path_utils.to_repo_relative(artifact_index_path, repo_root=REPO_ROOT)
    write_json(run_manifest_path, manifest)

    mismatch_script = REPO_ROOT / "book/experiments/hardened-runtime/mismatch_packets.py"
    if mismatch_script.exists():
        try:
            subprocess.run([str(PYTHON), str(mismatch_script)], check=True)
        except subprocess.CalledProcessError as exc:
            print(f"[!] mismatch packet refresh failed: {exc}")

    if stage_used and stage_root and not args.keep_stage:
        shutil.rmtree(stage_root, ignore_errors=True)

    write_json(LAUNCHCTL_DIR / "launchctl_last_run.json", {"label": label, "run_id": run_id})
    print(f"[+] wrote run manifest to {repo_out / 'run_manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
