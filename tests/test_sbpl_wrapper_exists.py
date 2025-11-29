from pathlib import Path


def test_sbpl_wrapper_built():
    wrapper = Path("book/api/SBPL-wrapper/wrapper")
    assert wrapper.exists(), "wrapper binary is missing; build with clang -o wrapper wrapper.c -lsandbox"
    assert wrapper.is_file()
