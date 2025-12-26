#!/usr/bin/env python3
"""
Launch runtime-adversarial via launchctl to avoid inheriting a sandboxed parent.

This runner bootstraps a transient LaunchAgent that executes run_adversarial.py
with --require-clean. The job aborts if apply preflight fails.
"""
from __future__ import annotations

import argparse
import json
import os
import plistlib
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book.api import path_utils

LAUNCHCTL = Path("/bin/launchctl")
PYTHON = Path("/usr/bin/python3")
RUNNER = Path(__file__).with_name("run_adversarial.py")
OUT_DIR = Path(__file__).with_name("out") / "launchctl"


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def build_plist(label: str, stdout_path: Path, stderr_path: Path, require_clean: bool) -> Dict[str, Any]:
    program = str(PYTHON if PYTHON.exists() else sys.executable)
    args = [program, str(RUNNER)]
    if require_clean:
        args.append("--require-clean")
    return {
        "Label": label,
        "ProgramArguments": args,
        "RunAtLoad": True,
        "WorkingDirectory": str(REPO_ROOT),
        "StandardOutPath": str(stdout_path),
        "StandardErrorPath": str(stderr_path),
        "EnvironmentVariables": {"PYTHONPATH": str(REPO_ROOT)},
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run runtime-adversarial via launchctl")
    parser.add_argument("--label", help="launchctl label override")
    parser.add_argument("--timeout", type=float, default=10.0, help="wait for output (seconds)")
    parser.add_argument("--keep-job", action="store_true", help="keep job loaded after run")
    parser.add_argument("--no-require-clean", action="store_true", help="allow run even if apply preflight fails")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not LAUNCHCTL.exists():
        print("[!] launchctl missing")
        return 2
    if not RUNNER.exists():
        print("[!] run_adversarial.py missing")
        return 2

    label = args.label or f"sandbox-lore.runtime-adversarial.{os.getpid()}"
    stdout_path = OUT_DIR / f"{label}.stdout.txt"
    stderr_path = OUT_DIR / f"{label}.stderr.txt"
    plist_path = OUT_DIR / f"{label}.plist"
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    require_clean = not args.no_require_clean
    plist = build_plist(label, stdout_path, stderr_path, require_clean=require_clean)
    plist_path.write_bytes(plistlib.dumps(plist))

    target = f"gui/{os.getuid()}"
    result: Dict[str, Any] = {
        "label": label,
        "target": target,
        "plist": path_utils.to_repo_relative(plist_path, repo_root=REPO_ROOT),
        "stdout": path_utils.to_repo_relative(stdout_path, repo_root=REPO_ROOT),
        "stderr": path_utils.to_repo_relative(stderr_path, repo_root=REPO_ROOT),
        "commands": [],
    }

    bootstrap_cmd = [str(LAUNCHCTL), "bootstrap", target, str(plist_path)]
    result["commands"].append(bootstrap_cmd)
    boot = subprocess.run(bootstrap_cmd, capture_output=True, text=True)
    result["bootstrap"] = {"rc": boot.returncode, "stderr": boot.stderr, "stdout": boot.stdout}
    if boot.returncode != 0:
        write_json(OUT_DIR / "launchctl_last_run.json", result)
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

    write_json(OUT_DIR / "launchctl_last_run.json", result)
    print(f"[+] launchctl run recorded in {OUT_DIR / 'launchctl_last_run.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
