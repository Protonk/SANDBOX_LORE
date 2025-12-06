import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def test_carton_generators_are_idempotent(tmp_path, monkeypatch):
    targets = [
        ROOT / "book/graph/mappings/carton/operation_coverage.json",
        ROOT / "book/graph/mappings/carton/operation_index.json",
        ROOT / "book/graph/mappings/carton/profile_layer_index.json",
        ROOT / "book/graph/mappings/carton/filter_index.json",
    ]
    before = {path: sha256(path) for path in targets}
    before_story = {
        "op": subprocess.check_output(
            [sys.executable, "-c", "from book.api.carton import carton_query as cq; import json; print(json.dumps(cq.operation_story('file-read*')) )"],
            cwd=ROOT,
        ).decode(),
        "profile": subprocess.check_output(
            [sys.executable, "-c", "from book.api.carton import carton_query as cq; import json; print(json.dumps(cq.profile_story('sys:bsd')) )"],
            cwd=ROOT,
        ).decode(),
        "filter": subprocess.check_output(
            [sys.executable, "-c", "from book.api.carton import carton_query as cq; import json; print(json.dumps(cq.filter_story('path')) )"],
            cwd=ROOT,
        ).decode(),
    }

    cmd = [
        sys.executable,
        "-m",
        "book.graph.mappings.run_promotion",
        "--generators",
        "carton-coverage,carton-indices",
    ]
    subprocess.check_call(cmd, cwd=ROOT)

    after = {path: sha256(path) for path in targets}
    after_story = {
        "op": subprocess.check_output(
            [sys.executable, "-c", "from book.api.carton import carton_query as cq; import json; print(json.dumps(cq.operation_story('file-read*')) )"],
            cwd=ROOT,
        ).decode(),
        "profile": subprocess.check_output(
            [sys.executable, "-c", "from book.api.carton import carton_query as cq; import json; print(json.dumps(cq.profile_story('sys:bsd')) )"],
            cwd=ROOT,
        ).decode(),
        "filter": subprocess.check_output(
            [sys.executable, "-c", "from book.api.carton import carton_query as cq; import json; print(json.dumps(cq.filter_story('path')) )"],
            cwd=ROOT,
        ).decode(),
    }
    assert before == after, json.dumps({"before": before, "after": after}, indent=2)
    assert before_story == after_story, json.dumps({"before_story": before_story, "after_story": after_story}, indent=2)
