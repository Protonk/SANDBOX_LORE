#!/usr/bin/env python3
"""
Run simple runtime probes under sandbox-exec for selected SBPL profiles.

Profiles exercised:
- bucket4:v1_read (allow file-read*)
- bucket5:v11_read_subpath (allow file-read* under /tmp/foo)

Results are written to out/runtime_results.json with per-probe exit codes.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "out"


PROFILE_PATHS = {
    "bucket4:v1_read": ROOT / "book/experiments/op-table-operation/sb/v1_read.sb",
    "bucket5:v11_read_subpath": ROOT / "book/experiments/op-table-operation/sb/v11_read_subpath.sb",
}


def ensure_tmp_files():
    # Create /tmp/foo and /tmp/bar for read/write probes
    for name in ["foo", "bar"]:
        p = Path("/tmp") / name
        p.write_text(f"runtime-checks {name}\n")


def run_probe(profile: Path, probe: Dict[str, Any]) -> Dict[str, Any]:
    target = probe.get("target")
    op = probe.get("operation")
    cmd: List[str]
    if op == "file-read*":
        cmd = ["cat", target]
    elif op == "file-write*":
        # append to target
        cmd = ["sh", "-c", f"echo runtime-check >> '{target}'"]
    else:
        cmd = ["true"]

    try:
        res = subprocess.run(
            ["sandbox-exec", "-f", str(profile), "--"] + cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return {
            "command": cmd,
            "exit_code": res.returncode,
            "stdout": res.stdout,
            "stderr": res.stderr,
        }
    except FileNotFoundError as e:
        return {"error": f"sandbox-exec missing: {e}"}
    except Exception as e:
        return {"error": str(e)}


def main():
    ensure_tmp_files()
    matrix_path = OUT / "expected_matrix.json"
    assert matrix_path.exists(), f"missing expected matrix: {matrix_path}"
    matrix = json.loads(matrix_path.read_text())
    profiles = matrix.get("profiles") or {}

    results = {}
    for key, rec in profiles.items():
        profile_path = PROFILE_PATHS.get(key)
        if not profile_path or not profile_path.exists():
            results[key] = {"status": "skipped", "reason": "no profile path"}
            continue
        probes = rec.get("probes") or []
        probe_results = []
        for probe in probes:
            probe_results.append({"name": probe.get("name"), **run_probe(profile_path, probe)})
        results[key] = {
            "status": "completed",
            "profile_path": str(profile_path),
            "probes": probe_results,
        }

    out_path = OUT / "runtime_results.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"[+] wrote {out_path}")


if __name__ == "__main__":
    main()
