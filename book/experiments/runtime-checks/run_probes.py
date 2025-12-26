#!/usr/bin/env python3
"""
Thin wrapper to run runtime probes using book.api.runtime_tools.
Defaults to writing artifacts into book/profiles/golden-triple/.
"""

from __future__ import annotations

from pathlib import Path
import sys
import json
import os
import ctypes
import errno

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from book.api.runtime_tools.core.models import WORLD_ID
from book.api.runtime_tools.core.normalize import write_matrix_observations
from book.api.runtime_tools import workflow


ROOT = Path(__file__).resolve().parent
MATRIX = ROOT / "out" / "expected_matrix.json"
OUT_DIR = ROOT / "out"
RUNTIME_PROFILES = OUT_DIR / "runtime_profiles"
KEY_SPECIFIC_RULES = {
    # /tmp resolves to /private/tmp on this host; add an alias so bucket-5 reads succeed.
    "bucket5:v11_read_subpath": ['(allow file-read* (subpath "/private/tmp/foo"))'],
    # Ensure metafilter_any denies match the /private/tmp symlink target for baz.
    "runtime:metafilter_any": [
        '(deny file-read* (literal "/private/tmp/baz.txt"))',
        '(deny file-write* (literal "/private/tmp/baz.txt"))',
    ],
}


def _sandbox_check_self() -> dict:
    info: dict = {"source": "sandbox_check"}
    try:
        lib = ctypes.CDLL("libsystem_sandbox.dylib", use_errno=True)
        fn = lib.sandbox_check
        fn.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
        fn.restype = ctypes.c_int
        rc = fn(os.getpid(), None, 0)
        err = ctypes.get_errno()
        info["rc"] = int(rc)
        if err:
            info["errno"] = int(err)
            info["errno_name"] = errno.errorcode.get(err)
    except Exception as exc:
        info["error"] = str(exc)
    return info


def main() -> int:
    run_id = os.environ.get("SANDBOX_LORE_RUN_ID")
    preflight_path = OUT_DIR / "run_preflight.json"
    preflight_path.parent.mkdir(parents=True, exist_ok=True)
    preflight = {
        "world_id": WORLD_ID,
        "run_id": run_id,
        "sandbox_check_self": _sandbox_check_self(),
    }
    preflight_path.write_text(json.dumps(preflight, indent=2))

    run = workflow.run_from_matrix(MATRIX, OUT_DIR, world_id=WORLD_ID, key_specific_rules=KEY_SPECIFIC_RULES)
    out_path = run.runtime_results
    try:
        events_path = OUT_DIR / "runtime_events.normalized.json"
        write_matrix_observations(MATRIX, out_path, events_path, world_id=WORLD_ID, run_id=run_id)
        print(f"[+] wrote normalized events to {events_path}")
        print(f"[+] runtime cut artifacts: {run.cut}")
    except Exception as e:
        print(f"[!] failed to normalize runtime events: {e}")
    print(f"[+] wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
