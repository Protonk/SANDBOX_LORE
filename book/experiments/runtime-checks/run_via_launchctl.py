#!/usr/bin/env python3
"""
Launch runtime-checks via launchctl to avoid inheriting a sandboxed parent.
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
RUNNER = Path(__file__).with_name("run_probes.py")
OUT_ROOT = Path(__file__).with_name("out")
LAUNCHCTL_DIR = OUT_ROOT / "launchctl"
STAGING_BASE = Path("/private/tmp/sandbox-lore-launchctl")
BASELINE = REPO_ROOT / "book" / "world" / "sonoma-14.4.1-23E224-arm64" / "world-baseline.json"


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def build_plist(
    label: str,
    stdout_path: Path,
    stderr_path: Path,
    seatbelt_callout: bool,
    repo_root: Path,
    runner_path: Path,
    run_id: str,
) -> Dict[str, Any]:
    program = str(PYTHON if PYTHON.exists() else sys.executable)
    args = [program, str(runner_path)]
    env = {"PYTHONPATH": str(repo_root), "SANDBOX_LORE_RUN_ID": run_id}
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
    seatbelt_callout: bool,
    stdout_rel: str | None,
    stderr_rel: str | None,
) -> Dict[str, Any]:
    preflight_path = out_root / "run_preflight.json"
    preflight = load_json(preflight_path)
    baseline = load_baseline()
    world_id = preflight.get("world_id") or baseline.get("world_id")
    channel = "launchd_clean" if preflight else "launchd_unclean"
    return {
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
        "preflight": {
            "path": path_utils.to_repo_relative(preflight_path, repo_root=repo_root)
            if preflight_path.exists()
            else None,
            "record": preflight or None,
        },
        "sandbox_check_self": (preflight.get("sandbox_check_self") if preflight else None),
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
    parser = argparse.ArgumentParser(description="Run runtime-checks via launchctl")
    parser.add_argument("--label", help="launchctl label override")
    parser.add_argument("--timeout", type=float, default=10.0, help="wait for output (seconds)")
    parser.add_argument("--keep-job", action="store_true", help="keep job loaded after run")
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
        print("[!] run_probes.py missing")
        return 2

    label = args.label or f"sandbox-lore.runtime-checks.{os.getpid()}"
    run_id = str(uuid.uuid4())
    stage_root: Path | None = None
    stage_used = not args.no_stage
    if stage_used:
        stage_root = stage_repo(label)
        repo_root = stage_root
        runner_path = stage_root / "book/experiments/runtime-checks/run_probes.py"
        job_out_dir = stage_root / "book/experiments/runtime-checks/out"
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

    seatbelt_callout = not args.no_seatbelt_callout
    plist = build_plist(
        label,
        stdout_path,
        stderr_path,
        seatbelt_callout=seatbelt_callout,
        repo_root=repo_root,
        runner_path=runner_path,
        run_id=run_id,
    )
    plist_path.write_bytes(plistlib.dumps(plist))

    target = f"gui/{os.getuid()}"
    result: Dict[str, Any] = {
        "label": label,
        "run_id": run_id,
        "target": target,
        "plist": path_utils.to_repo_relative(plist_path, repo_root=REPO_ROOT),
        "stdout": path_utils.to_repo_relative(stdout_path, repo_root=REPO_ROOT),
        "stderr": path_utils.to_repo_relative(stderr_path, repo_root=REPO_ROOT),
        "seatbelt_callout": seatbelt_callout,
        "stage_used": stage_used,
        "stage_root": str(stage_root) if stage_root else None,
        "runner": path_utils.to_repo_relative(RUNNER, repo_root=REPO_ROOT),
        "commands": [],
    }

    bootstrap_cmd = [str(LAUNCHCTL), "bootstrap", target, str(plist_path)]
    result["commands"].append(bootstrap_cmd)
    boot = subprocess.run(bootstrap_cmd, capture_output=True, text=True)
    result["bootstrap"] = {"rc": boot.returncode, "stderr": boot.stderr, "stdout": boot.stdout}
    if boot.returncode != 0:
        write_json(LAUNCHCTL_DIR / "launchctl_last_run.json", result)
        print("[!] launchctl bootstrap failed")
        return 2

    kick_cmd = [str(LAUNCHCTL), "kickstart", "-k", f"{target}/{label}"]
    result["commands"].append(kick_cmd)
    kick = subprocess.run(kick_cmd, capture_output=True, text=True)
    result["kickstart"] = {"rc": kick.returncode, "stderr": kick.stderr, "stdout": kick.stdout}

    waited = wait_for_output(stdout_path, stderr_path, args.timeout)
    result["waited"] = waited

    if not args.keep_job:
        bootout_cmd = [str(LAUNCHCTL), "bootout", target, str(plist_path)]
        result["commands"].append(bootout_cmd)
        bootout = subprocess.run(bootout_cmd, capture_output=True, text=True)
        result["bootout"] = {"rc": bootout.returncode, "stderr": bootout.stderr, "stdout": bootout.stdout}

    if stage_used and stage_root:
        try:
            sync_paths = sync_outputs(job_out_dir, OUT_ROOT, stdout_path, stderr_path, REPO_ROOT)
            if sync_paths:
                result["stdout_original"] = result.get("stdout")
                result["stderr_original"] = result.get("stderr")
                result.update(sync_paths)
        except Exception as exc:
            result["stage_sync_error"] = str(exc)
        if not args.keep_stage:
            try:
                shutil.rmtree(stage_root)
            except Exception as exc:
                result["stage_cleanup_error"] = str(exc)

    run_manifest = build_run_manifest(
        run_id=run_id,
        label=label,
        repo_root=REPO_ROOT,
        stage_used=stage_used,
        stage_root=stage_root,
        job_out_dir=job_out_dir,
        out_root=OUT_ROOT,
        seatbelt_callout=seatbelt_callout,
        stdout_rel=result.get("stdout"),
        stderr_rel=result.get("stderr"),
    )
    write_json(OUT_ROOT / "run_manifest.json", run_manifest)
    result["run_manifest"] = path_utils.to_repo_relative(OUT_ROOT / "run_manifest.json", repo_root=REPO_ROOT)

    write_json(LAUNCHCTL_DIR / "launchctl_last_run.json", result)
    print(f"[+] launchctl run recorded in {LAUNCHCTL_DIR / 'launchctl_last_run.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
