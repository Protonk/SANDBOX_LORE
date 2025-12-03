# Research Report

## Scope
Track kernel symbol/string extraction runs for the 14.4.1-23E224 kernelcache and related builds. Outputs are kept under `out/<build>/kernel-symbols/` for reuse and comparison across runs.

## Current state
- Latest run (Dec 2 2025) completed in ~69s with ARM64 analyzers only; outputs at `out/14.4.1-23E224/kernel-symbols/`.
- `strings.json`: ~243k entries; ~205 entries contain sandbox/AppleMatch/mac_policy terms (addresses include `0x-7fffdf10f0` `com.apple.security.sandbox`, `0x-7fffdf3a68` `com.apple.kext.AppleMatch`).
- `symbols.json`: ~215 entries emitted by the `kernel_symbols.py` script.
- Initial data-define pass (no analysis, process-existing) on `0x-7fffdf10f0` (`com.apple.security.sandbox` TEXT) yielded a defined string with zero callers in `data_refs.json` (as expected without full analysis).
- Batch data-define (no analysis) across 11 sandbox/mac_policy targets: all defined, zero callers (LINKEDIT symbols remain null type/value).
- Track B comparison: re-ran `addr:0xffffff800020ef10` with analysis; still zero callers. Analysis completed ~59s with only ARM64 analyzers; no xrefs surfaced.
- String-refs pass (Dec 2): `kernel_string_refs.py` via `run_task.py kernel-string-refs --process-existing --exec` found three string hits (same sandbox/AppleMatch literals), zero symbol hits, zero external-library matches; references lists were empty. Output stored at `out/14.4.1-23E224/kernel-string-refs/string_references.json`.

## Next pivots
- Run `run_data_define.py` with `--process-existing --no-analysis` on key addresses (e.g., `0x-7fffdf10f0`, `0x-7fffdf3a68`, selected `_sandbox_*` symbols) to gather xrefs/callers.
- Use `run_task.py kernel-op-table --process-existing` if op-table mapping is needed alongside symbols.
- Keep analyzer runs under ARM64 defaults; only rerun full analysis if new pre-scripts or processor IDs change.
