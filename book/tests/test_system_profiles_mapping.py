import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIGESTS = ROOT / "book" / "graph" / "mappings" / "system_profiles" / "digests.json"
BASELINE_REF = "book/world/sonoma-14.4.1-23E224-arm64/world-baseline.json"


def baseline_host():
    return json.loads((ROOT / BASELINE_REF).read_text()).get("host") or {}


def test_digests_mapping_shape():
    assert DIGESTS.exists(), "missing system profile digests mapping"
    data = json.loads(DIGESTS.read_text())
    meta = data.get("metadata") or {}
    host = meta.get("host")
    assert host == BASELINE_REF
    assert baseline_host().get("build") == "23E224"
    assert "source_jobs" in meta
    # Basic profiles present
    profiles = data.get("profiles") or {}
    for key in ["sys:airlock", "sys:bsd", "sys:sample"]:
        assert key in profiles, f"missing digest for {key}"
