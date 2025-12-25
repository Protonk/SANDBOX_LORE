# shrink-trace Experiment

## Purpose
- Reproduce and instrument a trace-then-shrink workflow that bootstraps SBPL allow rules from sandbox violations and minimizes the resulting profile.

## Baseline & scope
- Host baseline: `world_id sonoma-14.4.1-23E224-arm64-dyld-2c0602c5`.
- Inputs: upstream `trace.sh`/`shrink.sh`, deterministic fixture `fixtures/sandbox_target.c`, instrumented tracer, and unified log output on this host.
- Out of scope: cross-version claims or promotion into shared mappings until runs are completed and validated.

## Deliverables / expected outcomes
- Output directory with `profile.sb`, `profile.sb.shrunk`, `metrics.tsv`, and per-iteration logs under `out/`.
- A summarized convergence story (iterations, new rules, shrink removals).
- A reproducible run path using `scripts/run_workflow.sh` and a matrix runner under `scripts/run_matrix.sh`.

## Plan & execution log
- Ran `scripts/run_workflow.sh` with defaults (`SEED_DYLD=1`, `IMPORT_DYLD_SUPPORT=1`, `NETWORK_RULES=parsed`, `SUCCESS_STREAK=2`, `DENY_SCOPE=all`).
- Trace required 6 iterations to reach a 2/2 success streak; the final profile has 37 lines (`metrics.tsv`).
- `sandbox_min` exited 0, so the profile parses and execs a trivial target when fixture execs are allowed.
- Preflight scan for the traced profile completed successfully before shrink.
- Pre-shrink validation (two consecutive runs) succeeded, confirming repeatable execution.
- Shrink completed via `scripts/shrink_instrumented.sh` and produced a minimized profile with 11 lines; shrink removed 26 lines and kept 10 (`shrink_stdout.txt`, `profile.sb.shrunk`).
- Network parsing observed 2 network deny messages, produced 2 network allow rules, and rejected 0 network rules into `bad_rules.txt`.
- Parsed network rules use SBPL-constrained host normalization (`*` or `localhost`) plus unix-socket `path-literal` mapping for path-shaped denies, with rule-level validation to prevent rc=65 profile parse failures.
- Shrunk profile passed both fresh and repeat validation runs, and lint checks passed for traced and shrunk profiles.
- Deny extraction now runs across all sandbox messages captured during the iteration window, so child-process denies are eligible for rule generation.

## Characterization suite (fixtures)
- `sandbox_target` (default): `out/` — 6 iterations, 37 traced lines, 11-line shrunk profile; passes fresh + repeat validation.
- `sandbox_net_required`: `out/net_required/` — 8 iterations, 43 traced lines, 12-line shrunk profile; shrunk profile retains `network-outbound (remote ip "*:2000")` as required.
- `sandbox_spawn`: `out/spawn/` — 7 iterations, 35 traced lines, 6-line shrunk profile; shrunk profile retains `process-fork` and `process-exec*` for `/usr/bin/id`, showing child-process denies were captured.

## Trace convergence criterion
- **Repeatable success:** stop only after `SUCCESS_STREAK` consecutive runs exit 0 and append 0 new rules on the final run(s). This ensures the traced profile is stable under repeated execution, which shrink relies on.
- **Why this matters (substrate-only context):** SBPL distinguishes `file-write-create` vs `file-write-data`, and operations like `truncate`/`ftruncate` fall under `file-write-data`. A profile that only allows create can pass once but fail on subsequent runs when `O_TRUNC` applies. See the external sandbox guide for the operation split and semantics. [1]

## Shrink success criterion
- **Fresh + repeat validation:** `profile.sb.shrunk` must succeed on a fresh workspace (no `./out/`) and on a repeat run without cleanup. This prevents shrink from removing first-run-only permissions like `file-write-create` while still requiring `file-write-data` for truncation on repeat runs. [1]

## Evidence & artifacts
- Current run outputs live under `book/experiments/shrink-trace/out/` (profile, logs, metrics, stdout captures).
- Run summary (host metadata + results): `book/experiments/shrink-trace/out/run_summary.txt`.
- Variant run summaries: `book/experiments/shrink-trace/out/net_required/run_summary.txt`, `book/experiments/shrink-trace/out/spawn/run_summary.txt`.
- Preflight scan output: `book/experiments/shrink-trace/out/preflight_scan.json`.
- Per-iteration preflight outputs are written alongside logs as `book/experiments/shrink-trace/out/logs/iter_<n>_preflight.json`.
- Trace status: `book/experiments/shrink-trace/out/trace_status.txt`.
- `sandbox_min` diagnostic outputs: `book/experiments/shrink-trace/out/sandbox_min_stdout.txt`, `book/experiments/shrink-trace/out/sandbox_min_stderr.txt`, `book/experiments/shrink-trace/out/sandbox_min_exitcode.txt`.
- Rejected rules (parse-guard failures): `book/experiments/shrink-trace/out/bad_rules.txt`.
- Pre-shrink validation outputs: `book/experiments/shrink-trace/out/pre_shrink_run1_exitcode.txt`, `book/experiments/shrink-trace/out/pre_shrink_run2_exitcode.txt`.
- Shrink output: `book/experiments/shrink-trace/out/shrink_stdout.txt`, `book/experiments/shrink-trace/out/profile.sb.shrunk`.
- Post-shrink validation outputs: `book/experiments/shrink-trace/out/post_shrink_fresh_exitcode.txt`, `book/experiments/shrink-trace/out/post_shrink_repeat_exitcode.txt`.
- Lint outputs: `book/experiments/shrink-trace/out/lint_profile_trace.txt`, `book/experiments/shrink-trace/out/lint_profile_shrunk.txt`.

## Blockers / risks
- Unified log access may be restricted (Full Disk Access or admin context required).
- The return-code stop condition can end tracing early if the target tolerates denies; the instrumented script now records non-zero return codes correctly.
- Network parsing relies on SBPL-constrained host normalization (`*` or `localhost`) and rule-level validation to avoid rc=65 poisoning; malformed rules are still possible for non-network ops (see `bad_rules.txt`).
- PID-agnostic deny extraction can capture unrelated sandbox denies during the iteration window; use `DENY_SCOPE=pid` when isolating a single process is required.

## Next steps
- Run `scripts/run_matrix.sh` to populate `out/summary.md` with a multi-knob matrix for the new fixtures.

[1]: https://reverse.put.as/wp-content/uploads/2011/09/Apple-Sandbox-Guide-v1.0.pdf "Apple Sandbox Guide v1.0"
