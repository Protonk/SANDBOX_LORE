# Ghidra headless scaffold (`dumps/ghidra/`)

Purpose: run repeatable, headless Ghidra jobs against the 14.4.1-23E224 artifacts in `dumps/Sandbox-private/`. Outputs stay under `dumps/ghidra/out/` and projects under `dumps/ghidra/projects/`; nothing leaves `dumps/`.

## Layout
- `scaffold.py` — command builder for headless runs; prints (or executes) `analyzeHeadless` invocations that import the KC or dylib and run task scripts.
- `scripts/` — Ghidra (Jython) stubs per task:
  - `kernel_symbols.py` — import KC and dump symbols/strings (fill in with real exports).
  - `kernel_tag_switch.py` — locate PolicyGraph dispatcher/tag switch.
  - `kernel_op_table.py` — locate operation pointer table in the KC.
- `.gitignore` — ignores `out/` and `projects/` so runs stay untracked.

## Usage (dry-run by default)
```sh
# Show the command for kernel symbols/strings without running it
python3 dumps/ghidra/scaffold.py kernel-symbols --ghidra-headless /path/to/analyzeHeadless

# Execute (requires Ghidra installed and env input files present)
python3 dumps/ghidra/scaffold.py kernel-symbols --ghidra-headless /path/to/analyzeHeadless --exec
```

Arguments:
- `task`: one of `kernel-symbols`, `kernel-tag-switch`, `kernel-op-table`.
- `--build-id`: defaults to `14.4.1-23E224`.
- `--ghidra-headless`: path to `analyzeHeadless` (env `GHIDRA_HEADLESS` also honored).
- `--exec`: actually run; otherwise the tool prints a shell-ready command.

## Safety rules
- Inputs always come from `dumps/Sandbox-private/<build>/...`.
- Outputs always land in `dumps/ghidra/out/<build>/<task>/`; projects in `dumps/ghidra/projects/`.
- Scripts live in `dumps/ghidra/scripts/`; do not move or copy host data into tracked trees.
