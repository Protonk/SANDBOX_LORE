#!/usr/bin/env python3
"""
Generate a joined per-op runtime story from the latest runtime cut.

Reads the canonical op/scenario mappings from book/graph/mappings/runtime_cuts/
and emits runtime_story.json alongside them. Updates runtime_manifest.json to
include a pointer to the story file so loaders can discover it.
"""

from __future__ import annotations

import json
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from book.api import path_utils
from book.api.runtime import story as rt_story

CUT_ROOT = ROOT / "book" / "graph" / "mappings" / "runtime_cuts"


def main() -> None:
    manifest_path = CUT_ROOT / "runtime_manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"missing runtime manifest at {manifest_path}; run promotion first")

    manifest = json.loads(manifest_path.read_text())
    scenarios_path = path_utils.ensure_absolute(manifest.get("scenarios"), ROOT)
    ops_path = path_utils.ensure_absolute(manifest.get("ops"), ROOT)

    story = rt_story.build_runtime_story(ops_path, scenarios_path)
    out_path = CUT_ROOT / "runtime_story.json"
    rt_story.write_runtime_story(story, out_path)

    manifest["runtime_story"] = path_utils.to_repo_relative(out_path, ROOT)
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"[+] wrote runtime story to {out_path}")


if __name__ == "__main__":
    main()
