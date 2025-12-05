import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "book" / "graph" / "carton" / "CARTON.json"


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
    for entry in files:
        path = ROOT / entry["path"]
        assert path.exists(), f"manifest path missing: {path}"
        expected = entry["sha256"]
        assert sha256(path) == expected, f"hash mismatch for {path}"


def test_carton_manifest_host():
    data = json.loads(MANIFEST.read_text())
    host = data.get("host") or {}
    assert host.get("build") == "23E224"
