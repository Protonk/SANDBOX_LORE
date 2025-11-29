# Runtime Checks – Notes

Use this file for dated, concise notes on progress, commands, and intermediate findings.

## 2025-12-10

- Experiment scaffolded (plan/report/notes). Aim: gather runtime allow/deny traces for bucket-4/bucket-5 and system profiles, landing results in `book/graph/mappings/runtime/`. Harness and probes not yet run.

## 2025-12-11

- Defined initial probe matrix in `out/expected_matrix.json` targeting bucket-4 (`v1_read`) and bucket-5 (`v11_read_subpath`) profiles from `op-table-operation`, plus placeholders for system profiles. Expectations cover read/write on `/etc/hosts` and `/tmp/foo` aligned with SBPL allows/denies. Runtime harness not run yet.
- Added stub `out/runtime_results.json` (status: not-run) to track expectations until harness is executed. Guardrail `tests/test_runtime_matrix_shape.py` ensures bucket profiles/probes remain in the matrix.

## 2025-12-12

- Implemented simple `run_probes.py` harness using `sandbox-exec` against SBPL profiles (`v1_read.sb`, `v11_read_subpath.sb`); creates `/tmp/foo`/`/tmp/bar` and runs cat/echo probes. Results written to `out/runtime_results.json`.
- On this host, `sandbox-exec` failed to apply both profiles (`exit_code=71`, `sandbox_apply: Operation not permitted`), so all probes show sandbox-apply failure. System profiles remain skipped (no SBPL form). Need alternative harness or entitlement to run sandbox-exec under SIP.
