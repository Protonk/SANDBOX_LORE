import json
from pathlib import Path

from book.graph.mappings.runtime import generate_runtime_signatures as grs
from book.graph.mappings.runtime import promotion_packets


ROOT = Path(__file__).resolve().parents[2]
SIGNATURES = ROOT / "book" / "graph" / "mappings" / "runtime" / "runtime_signatures.json"


def load(path: Path):
    assert path.exists(), f"missing required file: {path}"
    return json.loads(path.read_text())


def test_expected_matrix_hash_matches_runtime_ir():
    packets = promotion_packets.load_packets(
        promotion_packets.DEFAULT_PACKET_PATHS,
        allow_missing=True,
    )
    expected_matrix, _world_id = promotion_packets.merge_expected_matrices(packets)
    expected_hash = grs.hash_expected_matrix(expected_matrix)

    signatures = load(SIGNATURES)
    meta = signatures.get("metadata") or {}
    recorded_hash = (meta.get("input_hashes") or {}).get("expected_matrix")

    assert recorded_hash == expected_hash, (
        "runtime_signatures expected_matrix hash does not match runtime IR; "
        "regenerate runtime_signatures after changing expected rows."
    )
