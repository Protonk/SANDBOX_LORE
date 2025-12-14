import json
from pathlib import Path

from book.graph.mappings.runtime import generate_runtime_signatures as grs


ROOT = Path(__file__).resolve().parents[2]
SIGNATURES = ROOT / "book" / "graph" / "mappings" / "runtime" / "runtime_signatures.json"


def load(path: Path):
    assert path.exists(), f"missing required file: {path}"
    return json.loads(path.read_text())


def test_expected_matrix_hash_matches_runtime_ir():
    runtime_ir = load(grs.RUNTIME_IR)
    # Mirror generator behavior: merge in adversarial expected matrix if present.
    if grs.ADV_EXPECTED.exists():
        adv_expected = load(grs.ADV_EXPECTED)
        runtime_ir.setdefault("expected_matrix", {}).setdefault("profiles", {}).update(
            (adv_expected.get("profiles") or {})
        )

    expected_matrix = runtime_ir.get("expected_matrix") or {}
    expected_hash = grs.hash_expected_matrix(expected_matrix)

    signatures = load(SIGNATURES)
    meta = signatures.get("metadata") or {}
    recorded_hash = (meta.get("input_hashes") or {}).get("expected_matrix")

    assert recorded_hash == expected_hash, (
        "runtime_signatures expected_matrix hash does not match runtime IR; "
        "regenerate runtime_signatures after changing expected rows."
    )
