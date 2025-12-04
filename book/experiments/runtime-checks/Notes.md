# Runtime Checks – Notes

Use this file for concise notes on progress, commands, and intermediate findings.

## Initial scaffold

- Experiment scaffolded (plan/report/notes). Aim: gather runtime allow/deny traces for bucket-4/bucket-5 and system profiles, landing results in `book/graph/mappings/runtime/`. Harness and probes not yet run.

## First harness attempts

- Defined initial probe matrix in `out/expected_matrix.json` targeting bucket-4 (`v1_read`) and bucket-5 (`v11_read_subpath`) profiles from `op-table-operation`, plus placeholders for system profiles. Expectations cover read/write on `/etc/hosts` and `/tmp/foo` aligned with SBPL allows/denies. Runtime harness not run yet.
- Added stub `out/runtime_results.json` (status: not-run) to track expectations until harness is executed. Guardrail `tests/test_runtime_matrix_shape.py` ensures bucket profiles/probes remain in the matrix.

## Early `sandbox-exec` failures

- Implemented simple `run_probes.py` harness using `sandbox-exec` against SBPL profiles (`v1_read.sb`, `v11_read_subpath.sb`); creates `/tmp/foo`/`/tmp/bar` and runs cat/echo probes. Results written to `out/runtime_results.json`.
- On this host, `sandbox-exec` failed to apply both profiles (`exit_code=71`, `sandbox_apply: Operation not permitted`), so all probes show sandbox-apply failure. System profiles remain skipped (no SBPL form). Need alternative harness or entitlement to run sandbox-exec under SIP.

## Bucket-4 vs bucket-5 expectations

- Re-ran `run_probes.py` under updated Codex permissions (full access) to see if `sandbox-exec` could apply profiles. Results still fail at launch: `sandbox-exec` cannot `execvp` the wrapped commands (`cat`, `sh`) with exit 71. For `v1_read` the errors are “Operation not permitted”; for `v11_read_subpath` they show “No such file or directory.” System profiles remain skipped (no paths provided). Effective runtime tracing is still blocked.

## Matrix shape and expectations

- Added a harness shim in `run_probes.py` to emit runtime-ready profiles under `out/runtime_profiles/` with `process-exec` plus baseline system file-read allowances; the subpath profile also flips to `(allow default)` with explicit denies for `/private/tmp/bar` reads and `/tmp/foo` writes to avoid the earlier sandbox-exec abort.
- Re-ran `run_probes.py`. Bucket-4 (`v1_read`) now executes: `/etc/hosts` and `/tmp/foo` reads succeed; `/etc/hosts` write is denied (exit 1). Bucket-5 (`v11_read_subpath`) now runs without crashing: `/tmp/foo` read succeeds; `/tmp/bar` read and `/tmp/foo` write both deny with exit 1.

## Wrapper harness integration

- Added expected/actual/match annotations to `run_probes.py` so runtime results carry a simple verdict comparison to `out/expected_matrix.json`.
- Re-ran `run_probes.py` on this host; `sandbox-exec` now fails to apply both bucket profiles (exit 71, `sandbox_apply: Operation not permitted`) despite the shims. All probes record `deny` due to apply failure; matches remain true only where expected=deny. System profiles still skipped (no SBPL path). Needs an alternative harness or SIP-relaxed environment to proceed.
- Added a local `sandbox_runner` (C shim calling `sandbox_init` on SBPL text, then `execvp`) and teach `run_probes.py` to prefer it over `sandbox-exec`. On this host, `sandbox_init` also fails with EPERM (“Operation not permitted”), so probes still show `deny` from apply failure. Conclusion: SIP/entitlement gate blocks both sandbox-exec and sandbox_init here; need a different environment or privileges to get runtime traces.

## Harness fixes and metafilter_any

- With danger-full-access, `sandbox_runner` now applies profiles: bucket-4/bucket-5 probes match expectations; added `runtime:allow_all` (mostly allows, except /etc/hosts write denied by OS perms) and `runtime:metafilter_any` (shows SIGABRT exit -6 on foo/bar reads, likely due to missing literal/param handling in shimmed profile). System profiles still skipped (no SBPL form). Need to debug metafilter profile crash and add SBPL/wrapper for system profiles.
- Reworked `metafilter_any` profile to an explicit allow-only form; still seeing exit -6 on allowed reads. Suspect shim/profile interaction; needs decoder check and maybe a simpler metafilter shape.

## Reader-based probes

- Added `sandbox_reader` (no exec; applies profile via sandbox_init and reads target). `run_probes.py` uses reader for `file-read*`.
- Extended `metafilter_any` to include `/private/tmp` literals; runtime probes now pass: foo/bar allowed (exit 0), other denied (open EPERM). Crash resolved.
- System profiles still skipped (no SBPL wrapper).

## Blob wrapper path

- Updated `out/expected_matrix.json` to point system profiles at compiled blobs and mark `mode: blob`.
- Taught `run_probes.py` to honor profile-level `mode` so blob probes run through `book/api/SBPL-wrapper/wrapper --blob`.
- Reran probes: bucket profiles and runtime shapes still pass; system profiles now apply via wrapper but `sandbox_apply` returns `EPERM` on this host, so all sys probes record deny (wrapper commands succeed, apply fails). Results recorded in `out/runtime_results.json`.

## Platform blob gate

- EPERM applies only to platform system blobs (`airlock`, `bsd`) when using blob mode; custom blobs apply fine. Likely platform-only provenance/credential check in the kernel when installing platform profile layers. SBPL imports remain a viable fallback; blob apply may need a more permissive host or explicit platform credentials.

## Recompiled system SBPL

- Recompiled `/System/Library/Sandbox/Profiles/airlock.sb` and `bsd.sb` via `sandbox_compile_string`; decoded headers match shipped blobs (same op_count/maybe_flags/profile_class heuristic).
- `wrapper --blob` apply results: `airlock` still `sandbox_apply: Operation not permitted`; `bsd` failed with `execvp` on `/bin/true` in this run (needs a simpler apply-only check), but sandbox_apply via ctypes returned rc=0 earlier.
- `sandbox_init` on SBPL text: `bsd` applies cleanly; `airlock` fails with `Operation not permitted` on this host. Conclusion: platform gating persists even when recompiling `airlock` SBPL as a user blob; use SBPL/compiled bsd as the only system profile for runtime here and treat airlock as expected-fail.

## Status update

- Marked `sys:airlock` as expected-fail locally; SBPL/compiled `bsd` remains usable. Need an apply-only probe for bsd to avoid execvp noise in blob mode.

## System profiles via SBPL

- Added `sys:airlock` and `sys:bsd` to runtime matrix using SBPL imports from `/System/Library/Sandbox/Profiles/*.sb`.
- Harness uses `sandbox_reader` for reads. `airlock` mostly aligns (write to /tmp foo denied by OS perms vs expected allow; adjust expectations). `bsd` denies /etc/hosts read/write (expected mismatch). Will need to revise expectations or add minimal shims for these profiles.

## Wrapper fix and SBPL mode (2025-12-04)

- Fixed `book/api/golden_runner` wrapper path to `book/api/SBPL-wrapper/wrapper` and forced blob-mode for `.sb.bin`.
- Updated the golden expected matrix to run bucket4/bucket5 via SBPL (mode `sbpl`) so `sandbox_reader` applies them without process-exec allowances; added a bucket5 entry to the golden matrix.
- Reran `run_probes.py` with PYTHONPATH set. Results: `runtime:allow_all` and `runtime:metafilter_any` = ok; bucket4 = ok; bucket5 = partial (one mismatch); platform blobs still skipped/untouched.
