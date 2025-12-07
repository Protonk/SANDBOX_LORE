import subprocess
from pathlib import Path


def test_dyld_libs_manifest_matches_slices():
    checker = Path(__file__).resolve().parents[2] / "book" / "graph" / "mappings" / "dyld-libs" / "check_manifest.py"
    assert checker.exists(), "missing dyld-libs manifest checker"
    res = subprocess.run(["python3", str(checker)], capture_output=True, text=True)
    if res.returncode != 0:
        msg = res.stdout + res.stderr
        raise AssertionError(f"dyld-libs manifest check failed: {msg}")
