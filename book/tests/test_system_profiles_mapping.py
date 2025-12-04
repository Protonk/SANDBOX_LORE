import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIGESTS = ROOT / "book" / "graph" / "mappings" / "system_profiles" / "digests.json"


def test_digests_mapping_shape():
    assert DIGESTS.exists(), "missing system profile digests mapping"
    data = json.loads(DIGESTS.read_text())
    meta = data.get("metadata") or {}
    host = meta.get("host") or {}
    assert host.get("build") == "23E224"
    assert "source_jobs" in meta
    # Basic profiles present
    for key in ["sys:airlock", "sys:bsd", "sys:sample"]:
        assert key in data, f"missing digest for {key}"
