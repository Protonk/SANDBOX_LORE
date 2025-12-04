#!/usr/bin/env python3
"""
Regenerate system profile digests mapping from validation IR only.

Inputs:
- book/graph/concepts/validation/out/experiments/system-profile-digest/digests_ir.json

Flow:
- Run validation driver with tag `system-profiles` (and smoke for dependencies).
- Require job experiment:system-profile-digest to be ok.
- Write book/graph/mappings/system_profiles/digests.json with host metadata and source_jobs.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any

ROOT = Path(__file__).resolve().parents[4]
IR_PATH = ROOT / "book" / "graph" / "concepts" / "validation" / "out" / "experiments" / "system-profile-digest" / "digests_ir.json"
STATUS_PATH = ROOT / "book" / "graph" / "concepts" / "validation" / "out" / "validation_status.json"
OUT_PATH = ROOT / "book" / "graph" / "mappings" / "system_profiles" / "digests.json"
EXPECTED_JOB = "experiment:system-profile-digest"


def run_validation():
    cmd = [sys.executable, "-m", "book.graph.concepts.validation", "--tag", "system-profiles"]
    subprocess.check_call(cmd, cwd=ROOT)


def load_status(job_id: str) -> Dict[str, Any]:
    status = json.loads(STATUS_PATH.read_text())
    jobs = {j.get("job_id") or j.get("id"): j for j in status.get("jobs", [])}
    job = jobs.get(job_id)
    if not job:
        raise RuntimeError(f"job {job_id} missing from validation_status.json")
    if job.get("status") != "ok":
        raise RuntimeError(f"job {job_id} not ok: {job.get('status')}")
    return job


def load_ir(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"missing IR: {path}")
    return json.loads(path.read_text())


def main() -> None:
    run_validation()
    job = load_status(EXPECTED_JOB)
    ir = load_ir(IR_PATH)

    host = ir.get("host") or {}
    profiles = ir.get("profiles") or {}
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    mapping = {
        "metadata": {
            "host": host,
            "generated": now,
            "source_jobs": ir.get("source_jobs") or [EXPECTED_JOB],
            "decoder": "book.api.decoder",
        },
    }
    mapping.update({k: v for k, v in profiles.items()})
    OUT_PATH.write_text(json.dumps(mapping, indent=2))
    print(f"[+] wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
