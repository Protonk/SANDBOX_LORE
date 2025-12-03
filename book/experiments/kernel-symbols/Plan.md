# Kernel symbols experiment — Plan

- Capture and iterate on kernel symbol/string outputs from Ghidra in a stable experiment location.
- Keep per-build outputs under `out/<build>/kernel-symbols/` for repeatable queries and follow-on scripts.
- Pivot from strings/symbols to targeted data-define and lookup runs to map sandbox-related artifacts.

Next pivots (Dec 3):
- Archive broadened string-refs outputs (done) and review notable hits for further addresses/symbols.
- Keep data-define targets in unsigned `addr:` form; run quick `--no-analysis --process-existing` passes for new string/symbol addresses and record callers (expected empty without full analysis).
- Optional helper: refresh `kernel-op-table` with `--process-existing --no-analysis` for cross-check against symbol/string hits.
- Prep targets for full-analysis runs (offline): highest-value addresses include `0xffffff800020ef10` (`com.apple.security.sandbox`), `0xffffff800020c598` (`com.apple.kext.AppleMatch`), and `0xffffff8002dd2920` (`com.apple.security.sandbox` data); adjust/add based on new string hits before running full analysis.
