# Lightweight redirector to load scripts from book/api/ghidra/scripts.
# Used to keep legacy script names functioning while code lives under book/.

import importlib.util
from pathlib import Path


NEW_SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "book" / "api" / "ghidra" / "scripts"


def run_script(script_name: str) -> None:
    target = NEW_SCRIPTS_DIR / script_name
    if not target.exists():
        raise FileNotFoundError(f"Redirect target missing: {target}")
    spec = importlib.util.spec_from_file_location(f"book_api_ghidra_{target.stem}", target)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load redirect target: {target}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if hasattr(module, "run"):
        module.run()
    else:
        raise AttributeError(f"Redirect target {target} has no run()")
