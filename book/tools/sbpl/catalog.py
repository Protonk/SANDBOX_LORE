#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence


BASE_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = BASE_DIR / "corpus" / "MANIFEST.json"


def _load_manifest(path: Path) -> Mapping[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"missing manifest: {path}")
    raw = json.loads(path.read_text())
    if not isinstance(raw, Mapping):
        raise ValueError("MANIFEST.json must be a JSON object")
    return raw


def _count_by(items: Iterable[Mapping[str, Any]], key: str) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for item in items:
        raw = item.get(key)
        k = raw if isinstance(raw, str) else "null"
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="sbpl-catalog")
    ap.add_argument("--json", action="store_true", help="Emit the full manifest JSON.")
    args = ap.parse_args(argv)

    manifest = _load_manifest(MANIFEST_PATH)
    if args.json:
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return 0

    entries = manifest.get("entries") or []
    if not isinstance(entries, list):
        raise ValueError("MANIFEST.json entries must be a list")
    by_family = _count_by([e for e in entries if isinstance(e, Mapping)], "family")
    total = sum(by_family.values())

    print(f"world_id: {manifest.get('world_id')}")
    print(f"entries: {total}")
    for family, count in by_family.items():
        print(f"- {family}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
