import subprocess
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run_script(relpath):
    script = ROOT / relpath
    assert script.exists(), f"missing script {script}"
    result = subprocess.run(["bash", str(script)], capture_output=True, text=True)
    return result


@pytest.mark.system
def test_compile_sample_sb():
    result = run_script("book/examples/sb/run-demo.sh")
    assert result.returncode == 0, result.stderr
    out = ROOT / "book/examples/sb/build/sample.sb.bin"
    assert out.exists(), "sample.sb.bin not generated"


@pytest.mark.system
def test_extract_system_profiles():
    result = run_script("book/examples/extract_sbs/run-demo.sh")
    assert result.returncode == 0, result.stderr
    out_dir = ROOT / "book/examples/extract_sbs/build/profiles"
    assert (out_dir / "airlock.sb.bin").exists()
    assert (out_dir / "bsd.sb.bin").exists()
