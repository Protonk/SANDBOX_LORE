import json
from pathlib import Path


def _load_json(path: Path):
    assert path.exists(), f"missing {path}"
    return json.loads(path.read_text())


def test_node_layout_artifacts():
    root = Path(__file__).resolve().parents[2]
    summary = root / "book/experiments/node-layout/out/summary.json"
    data = _load_json(summary)
    assert isinstance(data, list)
    # Each entry should have expected keys.
    for entry in data:
        for key in ("name", "op_entries", "section_lengths"):
            assert key in entry


def test_op_table_operation_artifacts():
    root = Path(__file__).resolve().parents[2]
    summary = root / "book/experiments/op-table-operation/out/summary.json"
    data = _load_json(summary)
    assert isinstance(data, list)
    op_map = _load_json(root / "book/experiments/op-table-operation/out/op_table_map.json")
    assert "profiles" in op_map


def test_op_table_vocab_alignment_artifacts():
    root = Path(__file__).resolve().parents[2]
    align = _load_json(root / "book/experiments/op-table-vocab-alignment/out/op_table_vocab_alignment.json")
    assert "records" in align
    assert isinstance(align["records"], list)
