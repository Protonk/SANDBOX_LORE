#!/usr/bin/env python3
"""
Thin wrapper to run runtime probes using book.api.runtime_tools.
Defaults to writing artifacts into book/profiles/golden-triple/.
"""

from __future__ import annotations

from pathlib import Path
import sys
import json

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


def main() -> int:
    run = workflow.run_from_matrix(MATRIX, OUT_DIR, world_id=WORLD_ID, key_specific_rules=KEY_SPECIFIC_RULES)
    out_path = run.runtime_results
    try:
        events_path = OUT_DIR / "runtime_events.normalized.json"
        write_matrix_observations(MATRIX, out_path, events_path, world_id=WORLD_ID)
        print(f"[+] wrote normalized events to {events_path}")
        print(f"[+] runtime cut artifacts: {run.cut}")
    except Exception as e:
        print(f"[!] failed to normalize runtime events: {e}")
    print(f"[+] wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
