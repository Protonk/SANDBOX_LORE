import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "book" / "api" / "carton" / "CARTON.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def test_carton_manifest_hashes():
    assert MANIFEST.exists(), "missing CARTON manifest"
    data = json.loads(MANIFEST.read_text())
    files = data.get("files") or []
    assert files, "manifest contains no files"
    assert "generated_at" not in data
    expected = {
        "book/graph/mappings/vocab/ops.json",
        "book/graph/mappings/vocab/filters.json",
        "book/graph/mappings/runtime/runtime_signatures.json",
        "book/graph/mappings/system_profiles/digests.json",
        "book/graph/mappings/carton/operation_coverage.json",
        "book/graph/mappings/carton/operation_index.json",
        "book/graph/mappings/carton/profile_layer_index.json",
        "book/graph/mappings/carton/filter_index.json",
        "book/graph/mappings/carton/concept_index.json",
        "book/graph/concepts/validation/out/experiments/runtime-checks/runtime_results.normalized.json",
        "book/graph/concepts/validation/out/experiments/field2/field2_ir.json",
        "book/graph/concepts/validation/out/experiments/system-profile-digest/digests_ir.json",
        "book/graph/concepts/validation/out/vocab_status.json",
        "book/graph/concepts/validation/out/validation_status.json",
    }
    manifest_paths = {entry["path"] for entry in files}
    assert manifest_paths == expected, f"manifest paths mismatch: {manifest_paths ^ expected}"
    for entry in files:
        path = ROOT / entry["path"]
        assert path.exists(), f"manifest path missing: {path}"
        expected = entry["sha256"]
        assert sha256(path) == expected, f"hash mismatch for {path}"


def test_carton_manifest_host():
    data = json.loads(MANIFEST.read_text())
    host = data.get("host") or {}
    assert host.get("build") == "23E224"
