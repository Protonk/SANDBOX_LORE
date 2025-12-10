"""
Apply the compiled entitlement-diff profiles via SBPL-wrapper and run
simple network/mach probes. Results are written to out/runtime_results.json.
"""

from __future__ import annotations

import json
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List

from book.api.path_utils import find_repo_root, to_repo_relative

REPO_ROOT = find_repo_root(Path(__file__))
WRAPPER = REPO_ROOT / "book" / "api" / "SBPL-wrapper" / "wrapper"
ENT_SAMPLE_SRC = REPO_ROOT / "book" / "experiments" / "entitlement-diff" / "entitlement_sample"
MACH_PROBE_SRC = REPO_ROOT / "book" / "experiments" / "runtime-checks" / "mach_probe"
FILE_PROBE_SRC = REPO_ROOT / "book" / "api" / "file_probe" / "file_probe"
STAGE_DIR = Path("/private/tmp/entitlement-diff/app_bundle")
ENT_SAMPLE = STAGE_DIR / "entitlement_sample"
MACH_PROBE = STAGE_DIR / "mach_probe"
FILE_PROBE = STAGE_DIR / "file_probe"
CONTAINER_DIR = Path("/private/tmp/entitlement-diff/container")
FILE_PROBE_TARGET = CONTAINER_DIR / "runtime.txt"

PROFILES: Dict[str, Dict[str, Path]] = {
    "baseline": {
        "blob": REPO_ROOT / "book" / "experiments" / "entitlement-diff" / "sb" / "build" / "appsandbox-baseline.sb.bin",
        "sb": REPO_ROOT / "book" / "experiments" / "entitlement-diff" / "sb" / "build" / "appsandbox-baseline.expanded.sb",
    },
    "network_mach": {
        "blob": REPO_ROOT / "book" / "experiments" / "entitlement-diff" / "sb" / "build" / "appsandbox-network-mach.sb.bin",
        "sb": REPO_ROOT / "book" / "experiments" / "entitlement-diff" / "sb" / "build" / "appsandbox-network-mach.expanded.sb",
    },
}

TESTS: List[Dict[str, object]] = [
    {"id": "network_bind", "command": [str(ENT_SAMPLE)]},
    {"id": "network_outbound_localhost", "command": ["/usr/bin/nc", "-z", "-w", "2", "127.0.0.1", "80"]},
    {"id": "mach_lookup_cfprefsd_agent", "command": [str(MACH_PROBE), "com.apple.cfprefsd.agent"]},
    {"id": "file_read", "command": [str(FILE_PROBE), "read", str(FILE_PROBE_TARGET)]},
    {"id": "file_write", "command": [str(FILE_PROBE), "write", str(FILE_PROBE_TARGET)]},
]


def run_probe(profile: Path, command: List[str]) -> Dict[str, object]:
    full_cmd = [str(WRAPPER), "--blob", str(profile), "--"] + command
    try:
        res = subprocess.run(full_cmd, capture_output=True, text=True, timeout=15)
        payload: Dict[str, object] = {
            "command": full_cmd,
            "exit_code": res.returncode,
            "stdout": res.stdout,
            "stderr": res.stderr,
        }
        if "sandbox_apply" in res.stderr:
            payload["status"] = "blocked"
            payload["notes"] = "sandbox_apply returned EPERM"
        elif res.returncode == 0:
            payload["status"] = "ok"
        else:
            payload["status"] = "deny"
        return payload
    except Exception as exc:  # pragma: no cover - runtime helper
        return {"command": full_cmd, "error": str(exc), "status": "error"}


def run_sandbox_exec(sb_path: Path, command: List[str]) -> Dict[str, object]:
    full_cmd = ["sandbox-exec", "-f", str(sb_path), "--"] + command
    try:
        res = subprocess.run(full_cmd, capture_output=True, text=True, timeout=15)
        return {
            "command": full_cmd,
            "exit_code": res.returncode,
            "stdout": res.stdout,
            "stderr": res.stderr,
            "status": "ok" if res.returncode == 0 else "nonzero",
        }
    except Exception as exc:  # pragma: no cover - runtime helper
        return {"command": full_cmd, "error": str(exc), "status": "error"}


def main() -> int:
    STAGE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ENT_SAMPLE_SRC, ENT_SAMPLE)
    shutil.copy2(MACH_PROBE_SRC, MACH_PROBE)
    shutil.copy2(FILE_PROBE_SRC, FILE_PROBE)
    CONTAINER_DIR.mkdir(parents=True, exist_ok=True)
    FILE_PROBE_TARGET.write_text("entitlement-diff runtime file\n")

    results: Dict[str, Dict[str, object]] = {}
    for profile_name, paths in PROFILES.items():
        blob = paths["blob"]
        sb_path = paths["sb"]
        profile_results: Dict[str, object] = {
            "profile_blob": to_repo_relative(blob, REPO_ROOT),
            "profile_sbpl": to_repo_relative(sb_path, REPO_ROOT),
        }
        for test in TESTS:
            probe_res = run_probe(blob, test["command"])  # type: ignore[arg-type]
            profile_results[test["id"]] = {"wrapper": probe_res}
            if probe_res.get("status") == "blocked":
                profile_results[test["id"]]["sandbox_exec"] = run_sandbox_exec(sb_path, test["command"])  # type: ignore[arg-type]
        results[profile_name] = profile_results

    out_path = REPO_ROOT / "book" / "experiments" / "entitlement-diff" / "out" / "runtime_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2) + "\n")
    print(f"[+] wrote {to_repo_relative(out_path, REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
