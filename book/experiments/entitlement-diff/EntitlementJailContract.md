# EntitlementJail Contract (entitlement-diff)

This document captures the stable EntitlementJail.app interface that the entitlement-diff tooling depends on. It is not a claim about sandbox semantics; it is a tool contract anchored by local fixtures.

## Purpose
- Provide a stable, host-bound contract for EntitlementJail CLI access used by `book/experiments/entitlement-diff/`.
- Keep the contract enforceable via fixtures and tests.
- Avoid over-claiming: these are tool interface observations on the Sonoma baseline.

## Scope
We depend on:
- `entitlement-jail run-xpc` for probes and correlation metadata.
- `sandbox-log-observer` for deny evidence (observer-only, outside the sandbox).

We do not rely on in-sandbox `log show` capture; log evidence is observer-first.

## CLI contract (observed)
The CLI help text must include:
- `run-xpc` with `--log-stream`, `--log-path-class` + `--log-name`, `--log-predicate`.
- `run-xpc` with `--plan-id`, `--row-id`, `--correlation-id`.
- `sandbox-log-observer` with `--pid`, `--process-name`, `--start`, `--end`, `--last`.
- `sandbox-log-observer` with `--plan-id`, `--row-id`, `--correlation-id`.

See fixtures:
- `book/experiments/entitlement-diff/out/ej/contract/run-xpc.help.txt`
- `book/experiments/entitlement-diff/out/ej/contract/sandbox-log-observer.help.txt`

## JSON contract (observer-first)
We depend on these fields:

`run-xpc` response (JSON stdout):
- `data.details.service_pid` (or `probe_pid`/`pid`)
- `data.details.process_name`
- `data.details.correlation_id`
- `data.log_capture_status`
- `data.deny_evidence`

`sandbox-log-observer` response (JSON stdout):
- `kind: "sandbox_log_observer_report"`
- `data.pid` (int) and `data.process_name` (string)
- `data.observed_deny` (bool)
- `data.plan_id`, `data.row_id`, `data.correlation_id` (strings)
- `data.predicate` (string)

See fixtures:
- `book/experiments/entitlement-diff/out/ej/contract/observer.sample.json`

## Guardrails
Tests validate the help text and observer JSON shape using these fixtures. See:
- `book/tests/test_entitlementjail_contract.py`
