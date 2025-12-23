# frida-testing Notes

## Running log
- Command: cc -O0 -g -o book/experiments/frida-testing/targets/open_loop book/experiments/frida-testing/targets/open_loop.c
- Result: built the bootstrap target binary.
- Artifacts: `book/experiments/frida-testing/targets/open_loop`
- Status: ok
- Follow-up: run `book/experiments/frida-testing/run_frida.py` with a hook and capture the first JSONL output.

- Command: ./.venv/bin/python -c 'import sys,frida; print("py:",sys.executable); print("frida:",frida.__version__)'
- Result: confirmed venv Python and frida 17.5.2.
- Artifacts: none
- Status: ok
- Follow-up: run fs_open hook with a deterministic EACCES target.

- Command: ./.venv/bin/python book/experiments/frida-testing/run_frida.py --spawn book/experiments/frida-testing/targets/open_loop /tmp/frida_testing_noaccess --script book/experiments/frida-testing/hooks/fs_open.js --duration-s 2
- Result: runner terminated with exit code 139; events.jsonl empty.
- Artifacts: `book/experiments/frida-testing/out/04968c5a-ab8b-45d9-8d41-84f11f223d64`
- Status: blocked (signal 11 before any send() payloads)
- Follow-up: stabilize runner/hook so spawn captures fs-open events with errno.

- Command: ./.venv/bin/python book/experiments/frida-testing/run_frida.py --spawn book/experiments/frida-testing/targets/open_loop /etc/hosts --script book/experiments/frida-testing/hooks/discover_sandbox_exports.js --duration-s 1
- Result: runner terminated with signal 11 (Sandbox(Signal(11))); events.jsonl empty.
- Artifacts: `book/experiments/frida-testing/out/64dfc33f-3275-4656-94c3-a427dd129a95`
- Status: blocked (signal 11 before any send() payloads)
- Follow-up: stabilize runner/hook so export inventory is emitted.

- Command: uname -m; file ./.venv/bin/python; ./.venv/bin/python -c 'import platform,sys; print("machine:", platform.machine()); print("exe:", sys.executable)'; file book/experiments/frida-testing/targets/open_loop; file book/tools/entitlement/EntitlementJail.app/Contents/MacOS/entitlement-jail
- Result: host, venv Python, open_loop, and entitlement-jail are all arm64 (no Rosetta mismatch).
- Artifacts: none
- Status: ok
- Follow-up: proceed with attach-first tests.

- Command: sed -n '1,120p' ~/Library/Logs/DiagnosticReports/Python-2025-12-22-161938.ips
- Result: Process=Python; Parent=zsh; Termination=SIGNAL 11 (Segmentation fault); Exception Type=EXC_BAD_ACCESS (SIGSEGV); faulting thread includes frida-main-loop.
- Artifacts: ~/Library/Logs/DiagnosticReports/Python-2025-12-22-161938.ips
- Status: ok
- Follow-up: treat spawn as unstable; pivot to attach-first.

- Command: book/tools/entitlement/EntitlementJail.app/Contents/MacOS/entitlement-jail run-system /bin/sleep 30 (background) + ./.venv/bin/python book/experiments/frida-testing/run_frida.py --attach-pid <pid> --script book/experiments/frida-testing/hooks/smoke.js --duration-s 2
- Result: ProcessNotRespondingError (refused to load frida-agent or terminated during injection); events.jsonl contains runner-exception.
- Artifacts: `book/experiments/frida-testing/out/5b0825cf-b3be-4a24-9a98-37fd4da5cb2f`
- Status: blocked (attach failed before any send() payloads)
- Follow-up: review helper/target crash reports; verify if CLI attach behaves differently.

- Command: sed -n '1,120p' ~/Library/Logs/DiagnosticReports/frida-helper-2025-12-22-170859.ips
- Result: Process=frida-helper; Parent=Python; Termination=SIGNAL 4 (Illegal instruction); Exception Type=EXC_BAD_ACCESS (SIGILL).
- Artifacts: ~/Library/Logs/DiagnosticReports/frida-helper-2025-12-22-170859.ips
- Status: ok
- Follow-up: treat as Frida helper-layer crash during attach.

- Command: sed -n '1,120p' ~/Library/Logs/DiagnosticReports/entitlement-jail-2025-12-22-170900.ips
- Result: Process=entitlement-jail; Parent=zsh; Termination=CODESIGNING Invalid Page (SIGKILL Code Signature Invalid); Exception Type=EXC_BAD_ACCESS.
- Artifacts: ~/Library/Logs/DiagnosticReports/entitlement-jail-2025-12-22-170900.ips
- Status: ok
- Follow-up: record as target crash during attach.

- Command: ./.venv/bin/python -c 'import frida; d=frida.get_local_device(); print(d)'
- Result: when run outside the Codex harness sandbox, prints `Device(id="local", ...)`; inside the harness sandbox this call can SIGSEGV, so frida-testing runs must be executed from a normal Terminal session (or otherwise outside the harness sandbox) to avoid misleading “plumbing” crashes.
- Artifacts: none
- Status: ok
- Follow-up: keep runs attach-first and outside harness sandbox.

- Command: book/experiments/frida-testing/targets/open_loop /etc/hosts (background) + ./.venv/bin/python book/experiments/frida-testing/run_frida.py --attach-pid <pid> --script book/experiments/frida-testing/hooks/smoke.js --duration-s 2
- Result: attach works; events.jsonl contains a `send` payload with `kind=smoke`.
- Artifacts: `book/experiments/frida-testing/out/0bd798d6-5986-4a26-a19c-28f7d577f240`
- Status: ok
- Follow-up: use the same attach target for export inventory and fs_open.

- Command: book/experiments/frida-testing/targets/open_loop /etc/hosts (background) + ./.venv/bin/python book/experiments/frida-testing/run_frida.py --attach-pid <pid> --script book/experiments/frida-testing/hooks/discover_sandbox_exports.js --duration-s 1
- Result: emits `kind=exports` with `module=libsystem_sandbox.dylib` and `count=87`.
- Artifacts: `book/experiments/frida-testing/out/903d8465-79c3-4ddf-ab01-83892c4a409c`
- Status: ok
- Follow-up: treat as an export-inventory witness only (no semantic claims).

- Command: DENY=/tmp/frida_testing_noaccess; chmod 000 "$DENY"; book/experiments/frida-testing/targets/open_loop "$DENY" (background) + ./.venv/bin/python book/experiments/frida-testing/run_frida.py --attach-pid <pid> --script book/experiments/frida-testing/hooks/fs_open.js --duration-s 2
- Result: emits repeated `kind=fs-open` events with `errno=13` (EACCES) for the deny path; this is an errno witness, not a sandbox attribution.
- Artifacts: `book/experiments/frida-testing/out/4f161bec-6ef0-4614-b070-58e9596f03a2`
- Status: ok
- Follow-up: keep this deny-path pattern for validating future hook packs.

## Entry template
- Command:
- Result:
- Artifacts:
- Status:
- Follow-up:
