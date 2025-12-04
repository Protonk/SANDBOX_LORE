# SBPL ↔ Graph ↔ Runtime – Notes

Use this file for concise notes on commands, hurdles, and intermediate results.

## Initial strict profiles

- Authored minimal profiles: `allow_all.sb`, `deny_all.sb`, `deny_except_tmp.sb`, `metafilter_any.sb` (param_path.sb exists but fails to compile without param injection).
- Compiled via `book/examples/sbsnarf/sbsnarf.py` (absolute paths) → binaries in `out/*.sb.bin`.
- Decoded headers/sections into `out/ingested.json` using `profile_ingestion.py` (modern-heuristic variant).
- Runtime probes: now running via `sandbox_runner`/`sandbox_reader`. allow_all runs (OS perms still deny `/etc/hosts` write); deny_all/deny_except_tmp align through runtime-checks. `metafilter_any` now passes (allow foo/bar, deny other) after adding `/private/tmp` literals and using reader to avoid exec overhead.
- Wrapper available: runtime-checks harness can exercise these compiled blobs via `book/api/SBPL-wrapper/wrapper --blob`; reuse that path for future triple captures instead of relying on `sandbox-exec`.
- System profiles: airlock remains EPERM on this host; bsd SBPL/compiled blob applies. Consider adding a `bsd`-like profile as a “system-style” triple if needed; otherwise keep the synthetic set as the runtime focus here.

## Param path adjustments (current run)

- Added a literal-filtered `(allow process-exec ...)` for `book/api/file_probe/file_probe` inside `profiles/param_path.sb` to keep a `(deny default)` helper alive during file probes.
- Recompiled the existing profiles with `python -m book.api.sbpl_compile.cli book/experiments/sbpl-graph-runtime/profiles/*.sb --out-dir book/experiments/sbpl-graph-runtime/out --no-preview`; `param_path.sb` failed with `invalid data type of path filter; expected pattern, got boolean`, likely because `(param "ROOT")` is unresolved in the current compiler wrapper. Other profiles compiled and were re-ingested into `out/ingested.json`.

## Concrete param profile + static expectations

- Added `profiles/param_path_concrete.sb` as a temporary instantiation with a literal ROOT at `/tmp/sbpl_rt/param_root` plus the process-exec escape hatch; compiled successfully to `out/param_path_concrete.sb.bin` and re-ingested into `out/ingested.json`.
- Created `out/static_expectations.json` capturing SBPL-level allow/deny expectations for the synthetic profiles (allow_all, deny_all, deny_except_tmp, metafilter_any, param_path_concrete) to serve as a machine-readable contract for upcoming runtime probes.
- `static_expectations.json` now carries best-effort node hooks (op_table raw entries and literal-matched node indices/tags where present) from the heuristic decoder; `param_path_concrete` links back to the template via `template_of` in `triples_manifest.json`.
- v0.1 of the contract is frozen with `schema_version: v0.1`, `runtime_join_key: expectation_id`, and per-expectation flags (`entrypoint_resolved`, `terminal_resolved`, `terminal_source`) to make provisional edges explicit. The runtime harness should log against `expectation_id` and record op/path/errno plus any observed op_index to keep runtime ↔ static joins stable.
- Runtime log schema captured at `book/experiments/runtime-checks/runtime_log_schema.v0.1.json`; `run_probes.py` now emits `expectation_id` (when present), op/path, and a structured `runtime_result`/`violation_summary` so runtime outputs can key back to static expectations.
