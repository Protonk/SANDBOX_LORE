import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_runtime_matrix_has_bucket_profiles():
    path = ROOT / "book" / "experiments" / "runtime-checks" / "out" / "expected_matrix.json"
    assert path.exists(), "expected runtime expected_matrix.json"
    matrix = json.loads(path.read_text())
    profiles = matrix.get("profiles") or {}
    for key in ["bucket4:v1_read", "bucket5:v11_read_subpath"]:
        assert key in profiles, f"missing runtime profile {key}"
        probes = profiles[key].get("probes") or []
        assert probes, f"expected probes for {key}"
