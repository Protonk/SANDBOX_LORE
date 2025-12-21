#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book.api.path_utils import to_repo_relative  # type: ignore
from book.api.profile_tools.identity import baseline_world_id  # type: ignore


BASE_DIR = Path(__file__).resolve().parent
CORPUS_DIR = BASE_DIR / "corpus"
SOURCES_PATH = CORPUS_DIR / "SOURCES.json"
MANIFEST_PATH = CORPUS_DIR / "MANIFEST.json"

MANIFEST_SCHEMA_VERSION = 1


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _validate_relpath(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        raise ValueError(f"relative path expected, got absolute path: {value}")
    if ".." in path.parts:
        raise ValueError(f"relative path may not contain '..': {value}")
    return path


def _load_sources(path: Path) -> Mapping[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"missing sources file: {path}")
    raw = json.loads(path.read_text())
    if not isinstance(raw, Mapping):
        raise ValueError("SOURCES.json must be a JSON object")
    return raw


def _iter_entries(raw: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    entries = raw.get("entries")
    if not isinstance(entries, list):
        raise ValueError("SOURCES.json entries must be a list")
    out: List[Mapping[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ValueError("SOURCES.json entries must be JSON objects")
        out.append(entry)
    return out


def _derive_id(dest_relpath: str) -> str:
    stem = dest_relpath[:-3] if dest_relpath.endswith(".sb") else dest_relpath
    return stem.replace("/", "__")


def build_manifest(
    entries: Iterable[Mapping[str, Any]],
    *,
    copy_files: bool,
) -> Mapping[str, Any]:
    world_id = baseline_world_id(REPO_ROOT)
    records: List[Dict[str, Any]] = []

    for entry in entries:
        dest_rel_raw = entry.get("dest_relpath")
        source_raw = entry.get("source_path")
        if not isinstance(dest_rel_raw, str):
            raise ValueError("entry.dest_relpath must be a string")
        if not isinstance(source_raw, str):
            raise ValueError("entry.source_path must be a string")

        dest_rel = _validate_relpath(dest_rel_raw)
        source_rel = _validate_relpath(source_raw)
        dest_path = CORPUS_DIR / dest_rel
        source_path = REPO_ROOT / source_rel

        if not source_path.exists():
            raise FileNotFoundError(f"missing source file: {source_path}")

        if copy_files:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_path, dest_path)

        if not dest_path.exists():
            raise FileNotFoundError(f"missing corpus file: {dest_path}")

        source_sha = _sha256_file(source_path)
        corpus_sha = _sha256_file(dest_path)
        if source_sha != corpus_sha:
            raise AssertionError(
                f"corpus copy hash mismatch for {to_repo_relative(dest_path, REPO_ROOT)}"
            )

        dest_rel_str = dest_rel.as_posix()
        record = {
            "id": entry.get("id") if isinstance(entry.get("id"), str) else _derive_id(dest_rel_str),
            "family": dest_rel_str.split("/", 1)[0],
            "path": to_repo_relative(dest_path, REPO_ROOT),
            "source_path": to_repo_relative(source_path, REPO_ROOT),
            "source_sha256": source_sha,
            "corpus_sha256": corpus_sha,
        }
        notes = entry.get("notes")
        if isinstance(notes, str) and notes:
            record["notes"] = notes
        records.append(record)

    records = sorted(records, key=lambda rec: rec["path"])
    return {
        "world_id": world_id,
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "entries": records,
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _diff_manifest(expected: Mapping[str, Any], existing: Mapping[str, Any]) -> List[str]:
    diffs: List[str] = []
    if expected.get("world_id") != existing.get("world_id"):
        diffs.append("world_id mismatch")
    if expected.get("manifest_schema_version") != existing.get("manifest_schema_version"):
        diffs.append("manifest_schema_version mismatch")
    expected_entries = expected.get("entries") or []
    existing_entries = existing.get("entries") or []
    if expected_entries != existing_entries:
        diffs.append("entries mismatch")
    return diffs


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="sync-corpus")
    ap.add_argument(
        "--check",
        action="store_true",
        help="Verify corpus files and MANIFEST.json without copying.",
    )
    args = ap.parse_args(argv)

    sources = _load_sources(SOURCES_PATH)
    world_id = sources.get("world_id")
    baseline_id = baseline_world_id(REPO_ROOT)
    if world_id != baseline_id:
        raise ValueError(f"SOURCES.json world_id mismatch: {world_id} != {baseline_id}")

    entries = _iter_entries(sources)
    manifest = build_manifest(entries, copy_files=not args.check)

    if args.check:
        if not MANIFEST_PATH.exists():
            raise FileNotFoundError(f"missing manifest: {MANIFEST_PATH}")
        existing = json.loads(MANIFEST_PATH.read_text())
        if not isinstance(existing, Mapping):
            raise ValueError("MANIFEST.json must be a JSON object")
        diffs = _diff_manifest(manifest, existing)
        if diffs:
            diff_summary = ", ".join(diffs)
            raise AssertionError(f"manifest out of sync: {diff_summary}")
        print(f"[ok] corpus matches {to_repo_relative(MANIFEST_PATH, REPO_ROOT)}")
    else:
        _write_json(MANIFEST_PATH, manifest)
        print(f"[+] wrote {to_repo_relative(MANIFEST_PATH, REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
