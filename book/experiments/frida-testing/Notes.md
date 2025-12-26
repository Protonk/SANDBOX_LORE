# frida-testing Notes

## Running log
- Action: added on_wait_ready callback support in book/api/entitlementjail/wait.py to enable pre-trigger Frida attach.
- Action: added book/experiments/frida-testing/run_ej_frida.py harness (capabilities_snapshot + attach-first run-xpc + observer capture + manifest).
- Action: updated book/experiments/frida-testing/hooks/fs_open_selftest.js to accept FRIDA_SELFTEST_PATH via RPC/config.
- Action: marked capture_sandbox_log.py and parse_sandbox_log.py as legacy (observer-first capture is the default).
- Action: removed legacy run artifacts under book/experiments/frida-testing/out/.
- Follow-up: run run_ej_frida.py outside the harness to capture new out/<run_id> artifacts.

- Command: ./.venv/bin/python book/experiments/frida-testing/run_ej_frida.py --profile-id fully_injectable --ack-risk fully_injectable --probe-id fs_op --script book/experiments/frida-testing/hooks/fs_open_selftest.js --probe-args --op open_read --path-class tmp --target specimen_file
- Result: run-xpc exited 1 with NSCocoaErrorDomain Code 4097 (connection to service named com.yourteam.entitlement-jail.ProbeService_fully_injectable); stdout JSON missing, log stream missing; Frida attached to PID 77857 and session detached after process termination.
- Artifacts: book/experiments/frida-testing/out/e1ee3f59-b895-49ab-ba4b-62d0bd27999b/manifest.json; book/experiments/frida-testing/out/e1ee3f59-b895-49ab-ba4b-62d0bd27999b/ej/run_xpc.json; book/experiments/frida-testing/out/e1ee3f59-b895-49ab-ba4b-62d0bd27999b/frida/events.jsonl.
- Status: blocked (no run-xpc witness JSON, service_pid missing).
- Follow-up: rerun with a clean service launch; inspect whether Frida attach is causing the XPC service to exit early.

- Command: ./.venv/bin/python book/experiments/frida-testing/run_ej_frida.py --profile-id fully_injectable --ack-risk fully_injectable --probe-id probe_catalog --script book/experiments/frida-testing/hooks/smoke.js
- Result: run-xpc ok; attach succeeded with pid_matches_service_pid true; observer reports captured; selftest path preparation failed with PermissionError (not needed for smoke).
- Artifacts: book/experiments/frida-testing/out/d8e2c72a-493d-4518-9dfa-b18b57a41e83/manifest.json; book/experiments/frida-testing/out/d8e2c72a-493d-4518-9dfa-b18b57a41e83/ej/run_xpc.json; book/experiments/frida-testing/out/d8e2c72a-493d-4518-9dfa-b18b57a41e83/frida/events.jsonl.
- Status: ok (attach works with smoke).
- Follow-up: avoid selftest preparation when using non-selftest hooks.

- Command: ./.venv/bin/python book/experiments/frida-testing/run_ej_frida.py --profile-id fully_injectable --ack-risk fully_injectable --probe-id fs_op --script book/experiments/frida-testing/hooks/smoke.js --no-prepare-selftest --probe-args --op open_read --path-class tmp --target specimen_file
- Result: run-xpc ok; attach succeeded with pid_matches_service_pid true; smoke hook emitted as expected; no deny evidence in observer output.
- Artifacts: book/experiments/frida-testing/out/41d1a763-bfc3-4dbf-9920-0335d001383b/manifest.json; book/experiments/frida-testing/out/41d1a763-bfc3-4dbf-9920-0335d001383b/ej/run_xpc.json; book/experiments/frida-testing/out/41d1a763-bfc3-4dbf-9920-0335d001383b/frida/events.jsonl.
- Status: ok (attach + fs_op works without hooks).
- Follow-up: try fs_open hooks now that attach is stable.

- Command: ./.venv/bin/python book/experiments/frida-testing/run_ej_frida.py --profile-id fully_injectable --ack-risk fully_injectable --probe-id fs_op --script book/experiments/frida-testing/hooks/fs_open.js --no-prepare-selftest --probe-args --op open_read --path-class tmp --target specimen_file
- Result: run-xpc ok; attach succeeded with pid_matches_service_pid true; fs_open hooks installed; no fs-open events emitted (open succeeded; LOG_SUCCESSES=false); script-config-error reported (configure missing).
- Artifacts: book/experiments/frida-testing/out/54bf34f2-a672-4eb2-8598-08861103d2f3/manifest.json; book/experiments/frida-testing/out/54bf34f2-a672-4eb2-8598-08861103d2f3/ej/run_xpc.json; book/experiments/frida-testing/out/54bf34f2-a672-4eb2-8598-08861103d2f3/frida/events.jsonl.
- Status: partial (hooks installed, but no error events for successful open).
- Follow-up: choose a deny path or enable success logging if we need fs-open events.

- Command: ./.venv/bin/python book/experiments/frida-testing/run_ej_frida.py --profile-id fully_injectable --ack-risk fully_injectable --probe-id fs_op --script book/experiments/frida-testing/hooks/fs_open_selftest.js --no-prepare-selftest --probe-args --op open_read --path-class tmp --target specimen_file
- Result: run-xpc exited 1 with NSCocoaErrorDomain Code 4097 (connection to service named com.yourteam.entitlement-jail.ProbeService_fully_injectable); stdout JSON missing, log stream missing; Frida session detached after process termination.
- Artifacts: book/experiments/frida-testing/out/6ba32d45-72c2-48fe-9dbe-ffc5ba8753f9/manifest.json; book/experiments/frida-testing/out/6ba32d45-72c2-48fe-9dbe-ffc5ba8753f9/ej/run_xpc.json; book/experiments/frida-testing/out/6ba32d45-72c2-48fe-9dbe-ffc5ba8753f9/frida/events.jsonl.
- Status: blocked (fs_open_selftest + fs_op not stable).
- Follow-up: retry with delay or alternate probe if selftest is required.

- Command: ./.venv/bin/python book/experiments/frida-testing/run_ej_frida.py --profile-id fully_injectable --ack-risk fully_injectable --probe-id fs_op --script book/experiments/frida-testing/hooks/fs_open_selftest.js --no-prepare-selftest --trigger-delay-s 1.0 --attach-timeout-s 10 --probe-args --op open_read --path-class tmp --target specimen_file
- Result: run-xpc exited 1 with NSCocoaErrorDomain Code 4097; stdout JSON missing, log stream missing; delay did not help.
- Artifacts: book/experiments/frida-testing/out/3317ec42-abe3-4ecb-a233-7e9ed5d3ca53/manifest.json; book/experiments/frida-testing/out/3317ec42-abe3-4ecb-a233-7e9ed5d3ca53/ej/run_xpc.json; book/experiments/frida-testing/out/3317ec42-abe3-4ecb-a233-7e9ed5d3ca53/frida/events.jsonl.
- Status: blocked (fs_open_selftest + fs_op still unstable).
- Follow-up: treat fs_open_selftest + fs_op as blocked until a different attach strategy is available.

- Command: ./.venv/bin/python book/experiments/frida-testing/run_ej_frida.py --profile-id fully_injectable --ack-risk fully_injectable --probe-id probe_catalog --script book/experiments/frida-testing/hooks/fs_open_selftest.js --no-prepare-selftest
- Result: run-xpc ok; attach succeeded with pid_matches_service_pid true; self-open executed and emitted fs-open with errno 13 (EACCES).
- Artifacts: book/experiments/frida-testing/out/b218b156-0b63-4265-8dc5-7aec41de3981/manifest.json; book/experiments/frida-testing/out/b218b156-0b63-4265-8dc5-7aec41de3981/ej/run_xpc.json; book/experiments/frida-testing/out/b218b156-0b63-4265-8dc5-7aec41de3981/frida/events.jsonl.
- Status: ok (fs_open_selftest works with probe_catalog).
- Follow-up: if fs_op needs selftest, consider running fs_open_selftest in a separate attach window from the fs_op probe.

- Command: ./.venv/bin/python book/experiments/frida-testing/run_ej_frida.py --profile-id fully_injectable --ack-risk fully_injectable --probe-id fs_op --script book/experiments/frida-testing/hooks/fs_open.js --skip-capabilities --service-name ProbeService_fully_injectable --probe-args --op open_read --path-class downloads --target specimen_file
- Result: run-xpc permission_error (errno=1) with deny_evidence=not_found; hooks installed, no fs-open events emitted.
- Artifacts: book/experiments/frida-testing/out/9e49bf0d-da44-4b2a-a928-af6a7ba6f274/manifest.json; book/experiments/frida-testing/out/9e49bf0d-da44-4b2a-a928-af6a7ba6f274/ej/run_xpc.json; book/experiments/frida-testing/out/9e49bf0d-da44-4b2a-a928-af6a7ba6f274/frida/events.jsonl.
- Status: partial (deny evidence missing; fs-open hooks did not observe the failure).
- Follow-up: force a direct open error via --path + chmod 000 to confirm hook coverage.

- Prep: created details.tmp_dir/ej_frida_denied.txt and chmod 000; removed after run.
- Command: ./.venv/bin/python book/experiments/frida-testing/run_ej_frida.py --profile-id fully_injectable --ack-risk fully_injectable --probe-id fs_op --script book/experiments/frida-testing/hooks/fs_open.js --skip-capabilities --service-name ProbeService_fully_injectable --probe-args --op open_read --path /Users/achyland/Library/Containers/com.yourteam.entitlement-jail.ProbeService_fully_injectable/Data/tmp/ej_frida_denied.txt --allow-unsafe-path
- Result: run-xpc permission_error (errno=13) with deny_evidence=captured; fs_open emitted __open/open events with errno 13 and backtrace frames pointing into InProcessProbeCore.probeFsOp.
- Artifacts: book/experiments/frida-testing/out/c1fe32d2-b058-43ff-81ca-836e346af8fa/manifest.json; book/experiments/frida-testing/out/c1fe32d2-b058-43ff-81ca-836e346af8fa/ej/run_xpc.json; book/experiments/frida-testing/out/c1fe32d2-b058-43ff-81ca-836e346af8fa/frida/events.jsonl.
- Status: ok (fs-open error events captured with deny evidence).
- Follow-up: use the explicit tmp_dir path + chmod 000 as the default deny-path recipe for fs_open.js.

- Command: ./.venv/bin/python book/experiments/frida-testing/run_ej_frida.py --profile-id fully_injectable --ack-risk fully_injectable --probe-id fs_op --script book/experiments/frida-testing/hooks/fs_open_funnel.js --skip-capabilities --service-name ProbeService_fully_injectable --probe-args --op open_read --path-class downloads --target specimen_file
- Result: run-xpc permission_error (errno=1) with deny_evidence=not_found; funnel hooks installed but no funnel-hit events (no errno 1/13 from open/openat/access/syscall).
- Artifacts: book/experiments/frida-testing/out/88533003-dc07-4b5a-96fa-30a157789c21/manifest.json; book/experiments/frida-testing/out/88533003-dc07-4b5a-96fa-30a157789c21/ej/run_xpc.json; book/experiments/frida-testing/out/88533003-dc07-4b5a-96fa-30a157789c21/frida/events.jsonl.
- Status: partial (downloads path-class failure did not surface via open/syscall hooks).
- Follow-up: treat downloads path-class permission_error as occurring before open; use explicit tmp_dir deny path when fs-open events are required.

- Command: ./.venv/bin/python book/experiments/frida-testing/run_ej_frida.py --profile-id fully_injectable --ack-risk fully_injectable --probe-id probe_catalog --script book/experiments/frida-testing/hooks/discover_sandbox_exports.js --skip-capabilities --service-name ProbeService_fully_injectable
- Result: exports from libsystem_sandbox.dylib enumerated; 87 sandbox_* exports captured; no errors.
- Artifacts: book/experiments/frida-testing/out/eca03911-40f3-4df0-a74d-9aba5f0c0c1e/manifest.json; book/experiments/frida-testing/out/eca03911-40f3-4df0-a74d-9aba5f0c0c1e/ej/run_xpc.json; book/experiments/frida-testing/out/eca03911-40f3-4df0-a74d-9aba5f0c0c1e/frida/events.jsonl.
- Status: ok (export enumeration worked).
- Follow-up: use this export list to confirm sandbox_set_trace_path/vtrace availability.

- Command: ./.venv/bin/python book/experiments/frida-testing/run_ej_frida.py --profile-id fully_injectable --ack-risk fully_injectable --probe-id probe_catalog --script book/experiments/frida-testing/hooks/sandbox_trace.js --skip-capabilities --service-name ProbeService_fully_injectable
- Result: sandbox_trace reported no sandbox_set_trace_path, sandbox_vtrace_enable, or sandbox_vtrace_report exports in libsystem_sandbox.dylib; trace unavailable.
- Artifacts: book/experiments/frida-testing/out/25d6ade2-0b08-40d2-b37c-fbcad882e11a/manifest.json; book/experiments/frida-testing/out/25d6ade2-0b08-40d2-b37c-fbcad882e11a/ej/run_xpc.json; book/experiments/frida-testing/out/25d6ade2-0b08-40d2-b37c-fbcad882e11a/frida/events.jsonl.
- Status: blocked (no trace exports to exercise).
- Follow-up: treat sandbox trace as unavailable on this host until a new export witness appears.

- Command: ./.venv/bin/python book/experiments/frida-testing/run_ej_frida.py --profile-id debuggable --probe-id fs_op --script book/experiments/frida-testing/hooks/fs_open_selftest.js --attach-seconds 60 --hold-open-seconds 40 --attach-timeout-s 10 --probe-args --op open_read --path-class tmp --target specimen_file
- Result: command timed out; frida attach failed with "refused to load frida-agent, or terminated during injection"; run_xpc/manifest not written.
- Artifacts: book/experiments/frida-testing/out/59e0530c-0817-49ad-ad0c-d824c7186b2c/ej/capabilities_snapshot.json; book/experiments/frida-testing/out/59e0530c-0817-49ad-ad0c-d824c7186b2c/frida/events.jsonl.
- Status: blocked (debuggable does not permit Frida attach in this run).
- Follow-up: try a different profile or service for attach; avoid long attach windows in the harness time limit.

- Command: ./.venv/bin/python book/experiments/frida-testing/run_ej_frida.py --profile-id debuggable --probe-id fs_op --script book/experiments/frida-testing/hooks/fs_open_selftest.js --attach-seconds 60 --hold-open-seconds 40 --attach-timeout-s 10 --probe-args --op open_read --path-class tmp --target specimen_file
- Result: second attempt timed out again; frida attach failed with the same error; run_xpc/manifest not written.
- Artifacts: book/experiments/frida-testing/out/c134a17d-2147-4031-9874-610a2e9de20b/ej/capabilities_snapshot.json; book/experiments/frida-testing/out/c134a17d-2147-4031-9874-610a2e9de20b/frida/events.jsonl.
- Status: blocked (repeatable attach failure under debuggable).
- Follow-up: treat debuggable as non-attachable for Frida in this experiment unless EntitlementJail changes.

- Command: ./.venv/bin/python book/experiments/frida-testing/run_ej_frida.py --profile-id plugin_host_relaxed --probe-id fs_op --script book/experiments/frida-testing/hooks/fs_open_selftest.js --attach-seconds 45 --hold-open-seconds 20 --attach-timeout-s 10 --probe-args --op open_read --path-class tmp --target specimen_file
- Result: run-xpc ok; frida attach failed with "unable to access process with pid ... from the current user account"; no fs-open events.
- Artifacts: book/experiments/frida-testing/out/6baf62bd-00c2-4bca-9d9c-aa6cd4807187/manifest.json; book/experiments/frida-testing/out/6baf62bd-00c2-4bca-9d9c-aa6cd4807187/ej/run_xpc.json; book/experiments/frida-testing/out/6baf62bd-00c2-4bca-9d9c-aa6cd4807187/frida/events.jsonl.
- Status: blocked (Frida attach denied for plugin_host_relaxed).
- Follow-up: keep attach-first work on fully_injectable; other profiles appear to block Frida injection on this host.

- Action: expanded fs_open_funnel.js to include mkdir/rename/unlink/creat/rmdir syscalls for fs_op failures.

- Command: ./.venv/bin/python book/experiments/frida-testing/run_ej_frida.py --profile-id dyld_env_enabled --ack-risk dyld_env_enabled --probe-id probe_catalog --script book/experiments/frida-testing/hooks/smoke.js --skip-capabilities --service-name ProbeService_dyld_env_enabled
- Result: run-xpc ok; frida attach denied with PermissionDeniedError (unable to access process pid).
- Artifacts: book/experiments/frida-testing/out/c15262bf-19b2-47c3-bc38-76234fd4bc3e/manifest.json; book/experiments/frida-testing/out/c15262bf-19b2-47c3-bc38-76234fd4bc3e/ej/run_xpc.json; book/experiments/frida-testing/out/c15262bf-19b2-47c3-bc38-76234fd4bc3e/frida/events.jsonl.
- Status: blocked (attach denied).
- Follow-up: treat dyld_env_enabled as non-attachable for Frida on this host.

- Command: ./.venv/bin/python book/experiments/frida-testing/run_ej_frida.py --profile-id jit_map_jit --ack-risk jit_map_jit --probe-id probe_catalog --script book/experiments/frida-testing/hooks/smoke.js --skip-capabilities --service-name ProbeService_jit_map_jit
- Result: run-xpc ok; frida attach denied with PermissionDeniedError (unable to access process pid).
- Artifacts: book/experiments/frida-testing/out/56efece2-00ed-4814-89a6-94de7649056a/manifest.json; book/experiments/frida-testing/out/56efece2-00ed-4814-89a6-94de7649056a/ej/run_xpc.json; book/experiments/frida-testing/out/56efece2-00ed-4814-89a6-94de7649056a/frida/events.jsonl.
- Status: blocked (attach denied).
- Follow-up: treat jit_map_jit as non-attachable for Frida on this host.

- Command: ./.venv/bin/python book/experiments/frida-testing/run_ej_frida.py --profile-id jit_rwx_legacy --ack-risk jit_rwx_legacy --probe-id probe_catalog --script book/experiments/frida-testing/hooks/smoke.js --skip-capabilities --service-name ProbeService_jit_rwx_legacy
- Result: run-xpc ok; frida attach denied with PermissionDeniedError (unable to access process pid).
- Artifacts: book/experiments/frida-testing/out/cb3bde87-6cb3-47cc-99ab-fc25621445a1/manifest.json; book/experiments/frida-testing/out/cb3bde87-6cb3-47cc-99ab-fc25621445a1/ej/run_xpc.json; book/experiments/frida-testing/out/cb3bde87-6cb3-47cc-99ab-fc25621445a1/frida/events.jsonl.
- Status: blocked (attach denied).
- Follow-up: treat jit_rwx_legacy as non-attachable for Frida on this host.

- Command: ./.venv/bin/python book/experiments/frida-testing/run_ej_frida.py --profile-id fully_injectable --ack-risk fully_injectable --probe-id fs_op --script book/experiments/frida-testing/hooks/fs_open_funnel.js --skip-capabilities --service-name ProbeService_fully_injectable --probe-args --op open_read --path-class downloads --target specimen_file
- Result: run-xpc permission_error (errno=1) with deny_evidence=captured; funnel-hit recorded for mkdirat with errno 1 while creating the downloads harness dir; no open/openat hits.
- Artifacts: book/experiments/frida-testing/out/dd0955c2-864a-4471-96b8-4b97e609f8b3/manifest.json; book/experiments/frida-testing/out/dd0955c2-864a-4471-96b8-4b97e609f8b3/ej/run_xpc.json; book/experiments/frida-testing/out/dd0955c2-864a-4471-96b8-4b97e609f8b3/frida/events.jsonl.
- Status: partial (downloads path-class failure observed at mkdirat; not an open hook).
- Follow-up: consider adding mkdirat to a dedicated fs_op funnel script or extending fs_open.js if we want per-op attribution.

- Action: added book/experiments/frida-testing/hooks/fs_op_funnel.js to log mkdir/rename/unlink/creat/rmdir calls regardless of errno.

- Command: ./.venv/bin/python book/experiments/frida-testing/run_ej_frida.py --profile-id fully_injectable --ack-risk fully_injectable --probe-id fs_op --script book/experiments/frida-testing/hooks/fs_op_funnel.js --skip-capabilities --service-name ProbeService_fully_injectable --probe-args --op open_read --path-class downloads --target specimen_file
- Result: run-xpc permission_error (errno=1) with deny_evidence=captured; fs-op-funnel logged mkdir/mkdirat calls (errno 17 in tmp, errno 2 and errno 1 in downloads harness path) with backtraces into InProcessProbeCore.probeFsOp.
- Artifacts: book/experiments/frida-testing/out/da23cd52-d323-41ae-bac7-a50f8aefe3cd/manifest.json; book/experiments/frida-testing/out/da23cd52-d323-41ae-bac7-a50f8aefe3cd/ej/run_xpc.json; book/experiments/frida-testing/out/da23cd52-d323-41ae-bac7-a50f8aefe3cd/frida/events.jsonl.
- Status: partial (downloads path-class failure observed at mkdirat; open not reached).
- Follow-up: use fs_op_funnel.js when mapping downloads path-class failures; add path_substr config if log volume grows.

## Entry template
- Command:
- Result:
- Artifacts:
- Status:
- Follow-up:
