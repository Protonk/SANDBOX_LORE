# Gate Minimizer (SBPL apply-gate delta debugger)

This tool turns “apply gating” (`sandbox_init`/`sandbox_apply` failing with `EPERM`) into a shrinkable target by delta-debugging SBPL text: it repeatedly deletes structure while preserving the predicate:

- `failure_stage == "apply"`
- `apply_report.errno == EPERM` (1)

The goal is to produce:

- a **minimal failing** SBPL fragment (still apply-gated with `EPERM`)
- a **minimal passing neighbor** (a one-deletion variation that successfully applies)

These two artifacts form a concrete boundary object that can be compared across profiles (and, if/when this repo grows beyond a single host, across world baselines).

## How it works (contract-driven)

The minimizer executes each candidate in a fresh process via `book/api/SBPL-wrapper/wrapper --sbpl … -- /usr/bin/true` and parses the JSONL tool markers using the runtime contract layer (`book/api/runtime/contract.py`). It does not infer from human stderr text.

## Usage

From repo root:

```sh
python3 book/tools/gate-minimizer/gate_minimizer.py \
  --input /System/Library/Sandbox/Profiles/airlock.sb \
  --out-dir book/tools/gate-minimizer/out/airlock
```

Options:
- `--wrapper`: override wrapper binary path (default: `book/api/SBPL-wrapper/wrapper`)
- `--command`: command executed after apply (default: `/usr/bin/true`)
- `--timeout-sec`: per-run timeout (default: 5)
- `--max-tests`: optional cap to prevent runaway minimization
- `--confirm N`: rerun `minimal_failing` and `passing_neighbor` `N` times (fresh processes) and record the `(failure_stage, errno)` distribution in `run.json`

Outputs (under `--out-dir`):
- `minimal_failing.sb`
- `passing_neighbor.sb`
- `run.json` (world + tool metadata, apply reports, and summary stats)
- `trace.jsonl`:
  - one JSON record per attempted candidate (apply report + phase classification inputs)
  - plus `ddmin_iteration` summary records (including `invalid` counts per iteration)

## Notes

- This tool is **host-bound** and should be used on the fixed SANDBOX_LORE baseline (`world_id sonoma-14.4.1-23E224-arm64-dyld-2c0602c5`).
- A “passing neighbor” is defined as “**not apply-gated**” (`failure_stage != "apply"`). It may still fail at bootstrap (e.g., `bootstrap_deny_process_exec`) and those outcomes are recorded in `run.json`.
- When running inside a harness that already constrains sandbox APIs, you may need to execute this tool “outside the harness sandbox” so `sandbox_init` can be exercised on the host.
