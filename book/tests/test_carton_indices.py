import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OP_INDEX = ROOT / "book" / "graph" / "mappings" / "carton" / "operation_index.json"
PROFILE_INDEX = ROOT / "book" / "graph" / "mappings" / "carton" / "profile_layer_index.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def test_operation_index_shape_and_sample():
    data = load(OP_INDEX)
    assert "metadata" in data and "operations" in data
    host = data["metadata"].get("host") or {}
    assert "generated_at" not in data["metadata"]
    assert host.get("build") == "23E224"
    op = data["operations"]["file-read*"]
    assert op["known"] is True
    assert isinstance(op["id"], int)
    assert "system" in op["profile_layers"]
    assert "sys:bsd" in op["system_profiles"]
    assert "bucket4:v1_read" in op["runtime_signatures"]
    counts = op["coverage_counts"]
    assert counts["system_profiles"] >= 1


def test_profile_layer_index_shape_and_sample():
    data = load(PROFILE_INDEX)
    assert "metadata" in data and "profiles" in data
    host = data["metadata"].get("host") or {}
    assert "generated_at" not in data["metadata"]
    assert host.get("build") == "23E224"
    bsd = data["profiles"]["sys:bsd"]
    assert bsd["layer"] == "system"
    assert bsd["ops"], "expected ops for sys:bsd"
    assert all("name" in op and "id" in op for op in bsd["ops"])
    assert "bucket4:v1_read" in bsd["runtime_signatures"]
    # Ensure ops are unique by id
    ids = [op["id"] for op in bsd["ops"]]
    assert len(ids) == len(set(ids))
