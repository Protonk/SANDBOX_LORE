from __future__ import annotations

import json
import shutil
from pathlib import Path

from book.api import path_utils

ROOT = Path(__file__).resolve().parents[3]
PROMOTION_PACKET = ROOT / "book" / "experiments" / "runtime-adversarial" / "out" / "promotion_packet.json"
DST_DIR = Path(__file__).resolve().parent / "out"

FILES_TO_COPY = [
    "runtime_results",
    "expected_matrix",
    "mismatch_packets",
    "impact_map",
    "runtime_events",
    "summary",
]


def main() -> None:
    DST_DIR.mkdir(exist_ok=True)
    if not PROMOTION_PACKET.exists():
        print(f"Missing promotion packet: {PROMOTION_PACKET}")
        return
    packet = json.loads(PROMOTION_PACKET.read_text())

    copied = []
    missing = []

    for name in FILES_TO_COPY:
        value = packet.get(name)
        if not value:
            missing.append(name)
            continue
        src = path_utils.ensure_absolute(Path(value), repo_root=ROOT)
        dst = DST_DIR / src.name
        if src.exists():
            shutil.copy2(src, dst)
            copied.append(dst)
        else:
            missing.append(name)

    if copied:
        print("Copied:")
        for path in copied:
            print(f"  {path}")
    else:
        print("No files copied; runtime-adversarial outputs not found.")

    if missing:
        print("Missing from source:")
        for name in missing:
            print(f"  {name}")

    print(f"Promotion packet source: {PROMOTION_PACKET}")


if __name__ == "__main__":
    main()
