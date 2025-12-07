import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OPS = ROOT / "book" / "graph" / "mappings" / "vocab" / "ops.json"
COVERAGE = ROOT / "book" / "graph" / "mappings" / "vocab" / "ops_coverage.json"


def test_ops_coverage_has_all_ops():
    ops = json.loads(OPS.read_text())["ops"]
    cov = json.loads(COVERAGE.read_text())
    assert len(cov) == len(ops), "coverage should have one entry per op"
    names = {o["name"] for o in ops}
    assert set(cov.keys()) == names
    # Known strong ops must have runtime evidence.
    for op in ["file-read*", "file-write*", "mach-lookup"]:
        entry = cov[op]
        assert entry["runtime_evidence"] is True, f"{op} should have runtime evidence"
        assert entry["structural_evidence"] is True
