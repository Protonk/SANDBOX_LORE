# Entitlement tools

This directory holds EntitlementJail.app and its adjacent fixtures. It is the home for App Sandbox + entitlement tooling on the Sonoma baseline.

## EntitlementJail.app
User guide: `EntitlementJail.md`

EntitlementJail is a macOS research/teaching tool for exploring App Sandbox and entitlements using a host-side CLI plus sandboxed XPC services. The guide documents workflows, logging/observer behavior, and output formats.

## Fixtures
Fixtures live under `fixtures/` and capture stable CLI/JSON shapes the tooling expects.

### Contract fixtures
- `fixtures/contract/run-xpc.help.txt`
- `fixtures/contract/sandbox-log-observer.help.txt`
- `fixtures/contract/observer.sample.json`

### Refresh (manual)
- `EntitlementJail.app/Contents/MacOS/entitlement-jail --help > fixtures/contract/run-xpc.help.txt`
- `EntitlementJail.app/Contents/MacOS/sandbox-log-observer --help > fixtures/contract/sandbox-log-observer.help.txt`
- Run `run-xpc --observe ...` and save the embedded `log_observer_report` JSON to `fixtures/contract/observer.sample.json`.
