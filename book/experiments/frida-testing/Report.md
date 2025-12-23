# frida-testing

## Purpose
Explore whether Frida-based instrumentation can provide host-bound runtime witnesses for sandbox behavior on the Sonoma 14.4.1 baseline. This experiment is exploratory; there is no host witness yet, and no claims are promoted beyond substrate theory.

## Baseline & scope
- world_id: sonoma-14.4.1-23E224-arm64-dyld-2c0602c5 (baseline: book/world/sonoma-14.4.1-23E224-arm64/world-baseline.json)
- Scope: Frida tooling, minimal probes, and runtime logs captured under this experiment.
- Out of scope: cross-version behavior, new vocabulary names, and promotion to mappings/CARTON without validation outputs.

## Deliverables / expected outcomes
- Bootstrap assets: target binary, Frida hooks, and a Python runner using the Frida API.
- Runtime logs or traces in `book/experiments/frida-testing/out/`, with repo-relative paths.
- Notes entries documenting runs, including failures or apply-stage gates.

## Plan & execution log
- Planned: verify the Frida CLI and Python bindings used by this repo's venv.
- Planned: define a minimal probe target and capture a first trace/log.
- Planned: map any observations to existing operations/filters or record as "we don't know yet".
- Planned: attach-first smoke witness using EntitlementJail; treat spawn as unstable on this host.
- Completed: added a minimal target, hook scripts, and a Python runner.
- Completed: attach-first plumbing witnesses against `open_loop` (smoke, export inventory, fs_open errno events).
- Attempted: spawn-based fs_open and sandbox export runs (terminated before emitting events).
- Attempted: attach-first smoke run against EntitlementJail CLI (runner exception; helper + target crashed).

## Evidence & artifacts
- Bootstrap target: `book/experiments/frida-testing/targets/open_loop.c`.
- Bootstrap binary: `book/experiments/frida-testing/targets/open_loop`.
- Hooks: `book/experiments/frida-testing/hooks/fs_open.js` and `book/experiments/frida-testing/hooks/discover_sandbox_exports.js`.
- Smoke hook: `book/experiments/frida-testing/hooks/smoke.js`.
- Runner: `book/experiments/frida-testing/run_frida.py`.

- Attach-first plumbing witness (baseline target `open_loop`):
  - Run `book/experiments/frida-testing/out/0bd798d6-5986-4a26-a19c-28f7d577f240` (smoke): script sha256 `d8711d9b959eb7a6275892f43b9130f3c825cbd15d8c0313fdc4a1a0e989b150`, event kinds `{"runner-start":1,"stage":4,"smoke":1,"session-detached":1}`.
  - Run `book/experiments/frida-testing/out/903d8465-79c3-4ddf-ab01-83892c4a409c` (discover_sandbox_exports): script sha256 `7051d15476ac8e44336368b57daf858a55f8cb13e923ff819b4dc0371f2826ce`, event kinds `{"runner-start":1,"stage":4,"exports":1,"session-detached":1}`.
    - Export payload: module `libsystem_sandbox.dylib`, count `87`, first 10 names: `sandbox_builtin_query`, `sandbox_check`, `sandbox_check_bulk`, `sandbox_check_by_audit_token`, `sandbox_check_by_reference`, `sandbox_check_by_uniqueid`, `sandbox_check_message_filter_integer`, `sandbox_check_message_filter_string`, `sandbox_check_process_signal_target`, `sandbox_check_protected_app_container`.
  - Run `book/experiments/frida-testing/out/4f161bec-6ef0-4614-b070-58e9596f03a2` (fs_open): script sha256 `724999594e57ad1c0ef73405ab1935bbb2ebe1c0b98adde90f824c2915c0372c`, event kinds `{"runner-start":1,"stage":4,"hook-installed":3,"fs-open":10,"session-detached":1}`; errno histogram `{"13":10}` using the deterministic deny path `/tmp/frida_testing_noaccess`.

- Earlier failures (pre-plumbing):
- Run `book/experiments/frida-testing/out/04968c5a-ab8b-45d9-8d41-84f11f223d64` (fs_open): script sha256 `666ea5243d87d008b41e5a444ae30f8cbced3802462ae659dc66db02659ab135`, event kinds `{}` (events.jsonl empty).
- Run `book/experiments/frida-testing/out/64dfc33f-3275-4656-94c3-a427dd129a95` (discover_sandbox_exports): script sha256 `7051d15476ac8e44336368b57daf858a55f8cb13e923ff819b4dc0371f2826ce`, event kinds `{}` (events.jsonl empty).
- Run `book/experiments/frida-testing/out/5b0825cf-b3be-4a24-9a98-37fd4da5cb2f` (smoke attach to EntitlementJail CLI): script sha256 `d8711d9b959eb7a6275892f43b9130f3c825cbd15d8c0313fdc4a1a0e989b150`, event kinds `{\"runner-exception\": 1}`.

## Blockers / risks
- Spawn runs are terminating before any send() payloads are recorded; treat spawn as unstable on this host until proven otherwise.
- Attach-first smoke run triggered frida-helper and target crashes; the helper crash suggests a Frida-layer instability and the target died with a code signing invalid-page kill.
- Running Frida inside the Codex harness sandbox can produce misleading “plumbing” crashes (for example, `frida.get_local_device()` SIGSEGV); run `frida-testing` captures from a normal Terminal session.

## Next steps
- Await instructions on target process and probe shape.
- Prefer attach-first plumbing until frida-helper/target crashes are understood.
