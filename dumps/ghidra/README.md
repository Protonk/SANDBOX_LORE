# Ghidra headless scaffold (`dumps/ghidra/`)

Canonical docs and scaffold now live at `book/api/ghidra/`:
- README: workflow, env knobs, task descriptions, tag-switch triage, and safety rules.
- Scaffold: `python -m book.api.ghidra.scaffold ...` (this `scaffold.py` is a shim for compatibility).

This directory remains the runtime workspace for headless runs:
- Inputs: `dumps/Sandbox-private/<build>/...` (git-ignored; do not move into tracked trees).
- Outputs: `dumps/ghidra/out/<build>/<task>/`, projects in `dumps/ghidra/projects/`, user/temp in `dumps/ghidra/user` and `dumps/ghidra/tmp` (all git-ignored).
- Scripts: `dumps/ghidra/scripts/` are redirectors to `book/api/ghidra/scripts/`.
