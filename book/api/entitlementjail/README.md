# entitlementjail (API)

This package wraps EntitlementJail.app for the Sonoma baseline. It provides a small Python surface for driving the `entitlement-jail` CLI and capturing deny evidence via `sandbox-log-observer` without binding tooling to experiment paths. This API expects EntitlementJail.app at `book/tools/entitlement/EntitlementJail.app`.
- Treat the EntitlementJail CLI as the source of truth for probe execution and log capture.
- Keep outputs host-bound and reproducible (no reliance on experiment-local paths).
- Prefer observer evidence for attribution; stream capture is retained as raw feed only.

## Entry points
- `book.api.entitlementjail.cli.run_xpc` (single probe)
- `book.api.entitlementjail.cli.run_matrix_group` (matrix group run + copy)
- `book.api.entitlementjail.cli.bundle_evidence` (bundle evidence + copy)
- `book.api.entitlementjail.wait.run_wait_xpc` / `run_probe_wait` (wait/attach flows)

## Logging defaults
Observer-first capture is enabled by default (`--observe`). Environment toggles:
- `EJ_LOG_MODE=stream|path_class` (default: stream)
- `EJ_LOG_OBSERVER=embedded|external|always|disabled` (default: embedded)
- `EJ_LOG_LAST=10s` (fallback window for observer)
- `EJ_LOG_PAD_S=2.0` (padding for `--start/--end` windows)
- `EJ_LOG_OBSERVER_DURATION_S=2.0`
- `EJ_LOG_OBSERVER_FORMAT=json|jsonl`
- `EJ_LOG_OBSERVER_OUTPUT=auto|<path>`

# Contract

The stable CLI and JSON shapes are documented below and guarded by fixtures in `book/tools/entitlement/fixtures/contract/`.

# EntitlementJail Contract

This document captures the stable EntitlementJail.app interface that the tooling depends on. It is not a claim about sandbox semantics; it is a tool contract anchored by local fixtures on the Sonoma baseline.

## Purpose
- Provide a stable, host-bound contract for EntitlementJail CLI access used by entitlement-diff and other tooling.
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
- `run-xpc` with `--log-stream <path|auto|stdout>` and `--json-out <path>`.
- `run-xpc` with `--observe`, `--observer-duration`, `--observer-format`, `--observer-output`, `--observer-follow`.
- `run-xpc` with `--plan-id`, `--row-id`, `--correlation-id`.
- `sandbox-log-observer` with `--pid`, `--process-name`, `--start`, `--end`, `--last`, `--duration`, `--follow`.
- `sandbox-log-observer` with `--format`, `--output`.
- `sandbox-log-observer` with `--plan-id`, `--row-id`, `--correlation-id`.

See fixtures:
- `book/tools/entitlement/fixtures/contract/run-xpc.help.txt`
- `book/tools/entitlement/fixtures/contract/sandbox-log-observer.help.txt`

## JSON contract (observer-first)
We depend on these fields:

`run-xpc` response (JSON stdout):
- `data.details.service_pid` (or `probe_pid`/`pid`)
- `data.details.process_name`
- `data.details.correlation_id`
- `data.log_capture_status`
- `data.log_capture_path`
- `data.log_capture_observed_deny`
- `data.log_capture_observed_lines`
- `data.deny_evidence`
- `data.log_observer_status`
- `data.log_observer_path`
- `data.log_observer_report`

`sandbox-log-observer` response (JSON stdout):
- `kind: "sandbox_log_observer_report"`
- `data.pid` (int) and `data.process_name` (string)
- `data.observed_deny` (bool)
- `data.plan_id`, `data.row_id`, `data.correlation_id` (strings)
- `data.predicate` (string)

`log-stream` response (JSON stdout or file):
- `kind: "sandbox_log_stream_report"`
- `data.pid` (int) and `data.process_name` (string)
- `data.observed_deny` (bool)
- `data.predicate` (string)

See fixtures:
- `book/tools/entitlement/fixtures/contract/observer.sample.json`

## Guardrails
Tests validate the help text and observer JSON shape using these fixtures. See:
- `book/tests/test_entitlementjail_contract.py`
