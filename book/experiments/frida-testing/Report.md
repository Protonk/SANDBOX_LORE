# frida-testing

## Purpose
Establish attach-first Frida witnesses for in-process sandbox behavior using EntitlementJail's process zoo on the Sonoma baseline. This experiment is exploratory; it does not promote claims beyond substrate theory without fresh host evidence.

## Baseline & scope
- world_id: sonoma-14.4.1-23E224-arm64-dyld-2c0602c5 (baseline: book/world/sonoma-14.4.1-23E224-arm64/world-baseline.json)
- Tools: EntitlementJail.app (book/tools/entitlement/EntitlementJail.app), Frida Python bindings, and book.api.entitlementjail.
- Scope: attach-first instrumentation inside EntitlementJail XPC services, with observer-first deny evidence capture.
- Out of scope: spawn-based Frida flows, new operation/filter names, or promotion to mappings/CARTON without validation outputs.

## Deliverables / expected outcomes
- Attach-first harness: book/experiments/frida-testing/run_ej_frida.py.
- Hook scripts: book/experiments/frida-testing/hooks/ (fs_open, fs_open_selftest, sandbox_trace, etc.).
- Output layout with manifest and observer logs under book/experiments/frida-testing/out/<run_id>/.

## Plan & execution log
- Completed: added on_wait_ready callback support in book/api/entitlementjail/wait.py to attach Frida before FIFO trigger.
- Completed: added run_ej_frida.py harness that runs capabilities_snapshot, attaches Frida, and captures EntitlementJail observer output.
- Completed: updated fs_open_selftest.js to accept a container-correct selftest path via RPC (FRIDA_SELFTEST_PATH fallback).
- Completed: labeled legacy unified-log scripts as deprecated; observer-first capture is now the default.
- Completed: removed legacy run artifacts from book/experiments/frida-testing/out/.
- Completed: probe_catalog + smoke (run_id d8e2c72a-493d-4518-9dfa-b18b57a41e83) attached successfully; observer output captured (selftest prep failed; not needed).
- Completed: fs_op + smoke (run_id 41d1a763-bfc3-4dbf-9920-0335d001383b) attached successfully; run-xpc ok.
- Completed: fs_op + fs_open.js (run_id 54bf34f2-a672-4eb2-8598-08861103d2f3) attached successfully; hooks installed, no fs-open events because open succeeded (LOG_SUCCESSES=false).
- Completed: fs_op + fs_open.js (run_id 9e49bf0d-da44-4b2a-a928-af6a7ba6f274) attached successfully; permission_error with deny_evidence=not_found; no fs-open events observed.
- Completed: fs_op + fs_open.js (run_id c1fe32d2-b058-43ff-81ca-836e346af8fa) attached successfully; explicit tmp_dir path with chmod 000 produced errno 13 fs-open events and deny_evidence=captured.
- Attempted: fs_op + fs_open_selftest (run_id e1ee3f59-b895-49ab-ba4b-62d0bd27999b) failed with XPC connection error.
- Attempted: fs_op + fs_open_selftest (run_id 6ba32d45-72c2-48fe-9dbe-ffc5ba8753f9) failed with XPC connection error.
- Attempted: fs_op + fs_open_selftest (run_id 3317ec42-abe3-4ecb-a233-7e9ed5d3ca53) failed with XPC connection error even with trigger delay.
- Completed: probe_catalog + fs_open_selftest (run_id b218b156-0b63-4265-8dc5-7aec41de3981) attached successfully; self-open emitted errno 13 (EACCES) fs-open event.
- Completed: fs_op + fs_open_funnel.js (run_id 88533003-dc07-4b5a-96fa-30a157789c21) attached successfully; no funnel-hit events for errno 1/13 under downloads path-class.
- Completed: fs_op + fs_open_funnel.js (run_id dd0955c2-864a-4471-96b8-4b97e609f8b3) attached successfully; mkdirat returned errno 1 while creating the downloads harness dir (deny evidence captured).
- Completed: fs_op + fs_op_funnel.js (run_id da23cd52-d323-41ae-bac7-a50f8aefe3cd) logged mkdir/mkdirat calls regardless of errno (errno 17 in tmp, errno 2/1 in downloads harness path).
- Completed: probe_catalog + discover_sandbox_exports.js (run_id eca03911-40f3-4df0-a74d-9aba5f0c0c1e) enumerated libsystem_sandbox exports (87 sandbox_* symbols).
- Completed: probe_catalog + sandbox_trace.js (run_id 25d6ade2-0b08-40d2-b37c-fbcad882e11a) reported no sandbox_set_trace_path/vtrace exports (trace unavailable).
- Attempted: fs_op + fs_open_selftest under debuggable (run_id 59e0530c-0817-49ad-ad0c-d824c7186b2c) timed out; Frida attach failed (no run_xpc/manifest).
- Attempted: fs_op + fs_open_selftest under debuggable (run_id c134a17d-2147-4031-9874-610a2e9de20b) timed out again; Frida attach failed (no run_xpc/manifest).
- Attempted: fs_op + fs_open_selftest under plugin_host_relaxed (run_id 6baf62bd-00c2-4bca-9d9c-aa6cd4807187) run-xpc ok but Frida attach denied.
- Attempted: probe_catalog + smoke under dyld_env_enabled (run_id c15262bf-19b2-47c3-bc38-76234fd4bc3e) run-xpc ok but Frida attach denied.
- Attempted: probe_catalog + smoke under jit_map_jit (run_id 56efece2-00ed-4814-89a6-94de7649056a) run-xpc ok but Frida attach denied.
- Attempted: probe_catalog + smoke under jit_rwx_legacy (run_id cb3bde87-6cb3-47cc-99ab-fc25621445a1) run-xpc ok but Frida attach denied.

## Evidence & artifacts
- Harness: book/experiments/frida-testing/run_ej_frida.py.
- Hooks: book/experiments/frida-testing/hooks/fs_open.js, book/experiments/frida-testing/hooks/fs_open_selftest.js, book/experiments/frida-testing/hooks/fs_open_funnel.js, book/experiments/frida-testing/hooks/fs_op_funnel.js, book/experiments/frida-testing/hooks/discover_sandbox_exports.js, book/experiments/frida-testing/hooks/sandbox_trace.js.
- EntitlementJail wait API: book/api/entitlementjail/wait.py (on_wait_ready callback).
- Successful runs:
  - book/experiments/frida-testing/out/d8e2c72a-493d-4518-9dfa-b18b57a41e83/manifest.json (probe_catalog + smoke).
  - book/experiments/frida-testing/out/41d1a763-bfc3-4dbf-9920-0335d001383b/manifest.json (fs_op + smoke).
  - book/experiments/frida-testing/out/54bf34f2-a672-4eb2-8598-08861103d2f3/manifest.json (fs_op + fs_open.js).
  - book/experiments/frida-testing/out/9e49bf0d-da44-4b2a-a928-af6a7ba6f274/manifest.json (fs_op + fs_open.js + downloads path-class; no fs-open events).
  - book/experiments/frida-testing/out/c1fe32d2-b058-43ff-81ca-836e346af8fa/manifest.json (fs_op + fs_open.js + explicit tmp_dir path; fs-open events captured).
  - book/experiments/frida-testing/out/88533003-dc07-4b5a-96fa-30a157789c21/manifest.json (fs_op + fs_open_funnel.js + downloads path-class; no funnel-hit events).
  - book/experiments/frida-testing/out/dd0955c2-864a-4471-96b8-4b97e609f8b3/manifest.json (fs_op + fs_open_funnel.js + downloads path-class; mkdirat errno 1).
  - book/experiments/frida-testing/out/da23cd52-d323-41ae-bac7-a50f8aefe3cd/manifest.json (fs_op + fs_op_funnel.js + downloads path-class; mkdir/mkdirat errno evidence).
  - book/experiments/frida-testing/out/eca03911-40f3-4df0-a74d-9aba5f0c0c1e/manifest.json (probe_catalog + discover_sandbox_exports.js).
  - book/experiments/frida-testing/out/25d6ade2-0b08-40d2-b37c-fbcad882e11a/manifest.json (probe_catalog + sandbox_trace.js; trace unavailable).
  - book/experiments/frida-testing/out/b218b156-0b63-4265-8dc5-7aec41de3981/manifest.json (probe_catalog + fs_open_selftest).
- Partial runs (Frida attach denied):
  - book/experiments/frida-testing/out/6baf62bd-00c2-4bca-9d9c-aa6cd4807187/manifest.json (fs_op + fs_open_selftest under plugin_host_relaxed).
  - book/experiments/frida-testing/out/c15262bf-19b2-47c3-bc38-76234fd4bc3e/manifest.json (probe_catalog + smoke under dyld_env_enabled).
  - book/experiments/frida-testing/out/56efece2-00ed-4814-89a6-94de7649056a/manifest.json (probe_catalog + smoke under jit_map_jit).
  - book/experiments/frida-testing/out/cb3bde87-6cb3-47cc-99ab-fc25621445a1/manifest.json (probe_catalog + smoke under jit_rwx_legacy).
- Timed-out runs (manifest missing):
  - book/experiments/frida-testing/out/59e0530c-0817-49ad-ad0c-d824c7186b2c/ej/capabilities_snapshot.json (debuggable; Frida attach failed; run_xpc missing).
  - book/experiments/frida-testing/out/c134a17d-2147-4031-9874-610a2e9de20b/ej/capabilities_snapshot.json (debuggable; Frida attach failed; run_xpc missing).
- Blocked runs (XPC connection error):
  - book/experiments/frida-testing/out/e1ee3f59-b895-49ab-ba4b-62d0bd27999b/manifest.json.
  - book/experiments/frida-testing/out/6ba32d45-72c2-48fe-9dbe-ffc5ba8753f9/manifest.json.
  - book/experiments/frida-testing/out/3317ec42-abe3-4ecb-a233-7e9ed5d3ca53/manifest.json.
- Output layout (fresh runs only):
  - book/experiments/frida-testing/out/<run_id>/manifest.json
  - book/experiments/frida-testing/out/<run_id>/ej/run_xpc.json
  - book/experiments/frida-testing/out/<run_id>/ej/logs/run_xpc.log
  - book/experiments/frida-testing/out/<run_id>/ej/logs/observer/<...>
  - book/experiments/frida-testing/out/<run_id>/frida/meta.json
  - book/experiments/frida-testing/out/<run_id>/frida/events.jsonl

## Run recipe (attach-first)
Example (Tier 2 profile requires --ack-risk):

```sh
./.venv/bin/python book/experiments/frida-testing/run_ej_frida.py \
  --profile-id fully_injectable \
  --ack-risk fully_injectable \
  --probe-id fs_op \
  --script book/experiments/frida-testing/hooks/fs_open_selftest.js \
  --probe-args --op open_read --path-class tmp --target specimen_file
```
Note: --probe-args consumes the remainder of the command line; keep it last.

## Blockers / risks
- Frida spawn remains unstable on this host; this experiment is attach-first only (partial, no current witness).
- Attach-first fs_op runs with fs_open_selftest repeatedly failed with NSCocoaErrorDomain Code 4097 (XPC connection error); treat fs_open_selftest + fs_op as blocked until a new attach strategy is available.
- Frida attach can crash inside the Codex harness sandbox; run captures from a normal Terminal session.
- sandbox_set_trace_path / vtrace exports were not present in libsystem_sandbox.dylib for fully_injectable (run_id 25d6ade2-0b08-40d2-b37c-fbcad882e11a); trace unavailable (blocked).
- fs_op with downloads path-class produced permission_error without fs-open events; extended funnel captured mkdirat errno 1 during harness dir creation, indicating failure before open (partial).
- Frida attach failed for debuggable, plugin_host_relaxed, dyld_env_enabled, jit_map_jit, and jit_rwx_legacy (injection refused / permission denied), limiting profile coverage.
- If multiple service PIDs exist, the attach PID may not match data.details.service_pid; check manifest.json for pid_matches_service_pid.

## Next steps
- For deterministic fs-open error events, use an explicit tmp_dir path (chmod 000) with fs_op --path --allow-unsafe-path; this yielded errno 13 events and deny evidence.
- If fs-open events are still missing, use fs_open_funnel.js to widen symbol coverage before extending fs_open.js.
- If downloads path-class attribution is required, use fs_op_funnel.js and focus on mkdirat/rename paths rather than open hooks.
- If a future EntitlementJail build reintroduces sandbox_set_trace_path or vtrace exports, rerun sandbox_trace.js and record the new status.
- If deny evidence is needed, use EntitlementJail observer output and keep attribution explicit.

## Appendix: legacy runs
Legacy run artifacts were removed from book/experiments/frida-testing/out/. No current host witness remains; treat any inference as substrate-only until new runs are captured.
