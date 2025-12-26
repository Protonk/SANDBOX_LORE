# entitlement-diff (EntitlementJail tooling)

This experiment treats EntitlementJail.app as a stable tool API and uses it to generate host-bound evidence about entitlements and sandbox outcomes.

## Observer-first logging
- Deny evidence is captured by the embedded `sandbox-log-observer` (via `run-xpc --observe` / `--log-stream`).
- `--log-stream` is used as a raw feed only; do not attribute denials from it without PID-scoped observer evidence.
- In-sandbox `log show` capture (`--log-path-class`) is treated as legacy and not relied on.

## Quick start
Run a known scenario:

```
PYTHONPATH=. python book/experiments/entitlement-diff/run_entitlementjail.py --scenario net_client
```

Run cross-profile network probes:

```
PYTHONPATH=. python book/experiments/entitlement-diff/run_entitlementjail.py --scenario net_op_groups
```

## Adding new probes (model pattern)
1) Add a scenario in `book/experiments/entitlement-diff/ej_scenarios.py`.
2) Use `run_xpc` (from `book/api/entitlementjail/cli.py`) or `run_wait_xpc` (from `book/api/entitlementjail/wait.py`).
3) Always pass a `log_path`, `plan_id`, and `row_id` so the observer output is correlated.
4) Consume `observer` (PID-scoped) output as the deny evidence source.

## Contract and tests
The stable CLI and JSON shapes are documented and guarded:
- Contract doc: `book/api/entitlementjail/README.md` (Contract section)
- Fixtures: `book/tools/entitlement/fixtures/contract/`
- Tests: `book/tests/test_entitlementjail_contract.py`

## Environment toggles
Defaults are observer-first:
- `EJ_LOG_MODE=stream` (default; `path_class` is legacy)
- `EJ_LOG_OBSERVER=embedded` (default)
- `EJ_LOG_LAST=10s` (fallback window)
- `EJ_LOG_PAD_S=2.0` (padding for `--start/--end` windows)
- `EJ_LOG_OBSERVER_DURATION_S=2.0` (live observer window; uses `log stream`)
- `EJ_LOG_OBSERVER_FORMAT=json` (observer output format)
- `EJ_LOG_OBSERVER_OUTPUT=auto` (observer output destination)
