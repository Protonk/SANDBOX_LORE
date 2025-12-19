# Entitlement Diff – Research Report

## Purpose
Trace how selected entitlements alter compiled sandbox profiles and the resulting allow/deny behavior. Ground the entitlement concept in concrete profile/filter/parameter changes and, where possible, runtime probes.

## Baseline & scope
- World: sonoma-14.4.1-23E224-arm64-dyld-2c0602c5 (SIP enabled).
- Tooling: `entitlement_sample` binaries, App Sandbox stubs under `sb/`, `build_profiles.py` to inline/compile, `diff_profiles.py` to decode/diff, `run_probes.py` for blob-applied runtime probes, and `book/tools/entitlement/EntitlementJail.app` as a planned second runtime runner intended to witness jail-run behavior under an App Sandbox parent. The jail runner is `run_probes_jail.py`.
- Entitlements: baseline has only app-sandbox; variant enables `com.apple.security.network.server` and a single mach-lookup global-name (`com.apple.cfprefsd.agent`).

## Deliverables / expected outcomes
- Minimal C sample and signed variants (`entitlement_sample`, `entitlement_sample_unsigned`) with extracted entitlements recorded in `out/*.entitlements.plist`.
- A reproducible method for deriving per-entitlement App Sandbox profiles suitable for decoding and comparison (App Sandbox stubs → expand/compile to blobs via libsandbox).
- Planned diffs that connect entitlement keys → SBPL parameters/filters → compiled graph deltas → runtime allow/deny behavior.
- A short manifest tying binaries, profiles, decoded diffs, and probe logs together for this host.
- A second runtime runner using `EntitlementJail.app` that captures behavior when executing probes under the jail (expected to reflect an App Sandbox parent), with structured outputs suitable for comparing against wrapper-applied behavior.
  - Skeleton witness: `out/jail_env_probe.json` establishes the observed `HOME`/`TMPDIR`/`PWD` under the jail.

## Plan & execution log
### Completed
- Sample program built (`entitlement_sample`) and unsigned variant captured with entitlements in `out/entitlement_sample*.entitlements.plist`.
- App Sandbox stubs derived from `book/profiles/textedit/application.sb` with pinned params/entitlements (`sb/appsandbox-*.sb`); `build_profiles.py` expands/compiles to `sb/build/*.expanded.sb` and `.sb.bin`.
- Decoded both blobs and wrote structural deltas to `out/profile_diffs.json` (ops present via op_table indices, literal adds/removals, literal_refs deltas, tag deltas) alongside raw decodes in `out/decoded_profiles.json`.
- Runtime probes via `book/api/SBPL-wrapper/wrapper --blob` with staged binaries under `/private/tmp/entitlement-diff/app_bundle/`:
  - baseline (app sandbox only): `entitlement_sample` bind denied (`bind: Operation not permitted`), `mach_probe com.apple.cfprefsd.agent` allowed.
  - network_mach (network.server + mach allowlist): bind allowed, mach-lookup allowed.
  Results recorded in `out/runtime_results.json`.
- Implemented the EntitlementJail-based runner (`run_probes_jail.py`) as a second runtime witness and executed an env-probe + exec-gate discriminant run:
  - Observed jail environment: `HOME=/Users/achyland/Library/Containers/com.yourteam.entitlement-jail/Data` (see `out/jail_env_probe.json`).
  - Per-run capture isolation: jail outputs are written under `stage_root/jail_out/<session_id>/...` to avoid stale `.done` reuse between runs (see `meta.session_id` in `out/jail_env_probe.json`).
  - Exec-gate discriminant (see `out/jail_env_probe.json` → `exec_gate`):
    - In-place system binary executes: `/usr/bin/true` is `executed`.
    - Relocated system binary fails: a staged copy of `/usr/bin/true` under `stage_root` is `blocked` (`rc=126`, `Operation not permitted`).
    - All staged probe Mach-Os (`file_probe`, `mach_probe`, `entitlement_sample{,_unsigned}`) are `blocked` with the same exec failure.
  - Authoritative denial witness (partial, runtime): kernel log capture shows `process-exec*` denies for the staged paths:
    - `out/jail_logs_exec_gate_relocated_true_c7c4fdfb854b7ca0.log` includes `deny(1) process-exec* .../relocated_true_c7c4fdfb854b7ca0`.
    - `out/jail_logs_exec_gate_file_probe_usage_c7c4fdfb854b7ca0.log` includes `deny(1) process-exec* .../file_probe`.
  - Because `process-exec*` is denied for staged paths on this host, the jail witness cannot yet execute our probe binaries from the container stage root; `out/jail_runtime_results.json` is therefore `blocked` with `failure_kind: EXEC_GATE_LOCATION_OR_WRITABLE_DENIED`.

### Planned
- With `process-exec*` denied for container-staged paths, the next phase is to decide whether to route around the exec gate or treat it as the witness conclusion.

  1) **Route around: bundle the probes (new witness variant)**
     - Build a separate, explicitly experimental App Sandbox parent runner that embeds `file_probe`, `mach_probe`, and the entitlement-diff samples as nested code inside the app bundle, then exec them from within the bundle.
     - Treat this as a distinct witness with its own provenance (codesign identity, hashes, entitlements) rather than modifying the notarized `EntitlementJail.app` in place.

  2) **Treat as conclusion (current witness)**
     - Record that, on this host baseline, an App Sandbox parent can execute in-place platform binaries but cannot `process-exec*` arbitrary staged binaries from its container stage root; therefore, parity vs wrapper-applied blobs is not measurable via this witness path without altering packaging/signing.

## Evidence & artifacts
- Source and build scaffolding for `entitlement_sample` under this experiment directory; extracted entitlements in `out/entitlement_sample*.entitlements.plist`.
- App Sandbox stubs and compiled outputs in `sb/` and `sb/build/` (expanded SBPL + blobs); build helper `build_profiles.py`.
- Decodes and structural diffs in `out/decoded_profiles.json` and `out/profile_diffs.json` (includes literal_refs and tag_literal_refs); manifest recorded in `out/manifest.json`.
- Runtime results in `out/runtime_results.json` (baseline: network bind/outbound denied, mach allowed, container file read/write allowed; network_mach: bind allowed, mach allowed, file read/write allowed, outbound `nc` to localhost still denied).
- Jail-run witness artifacts: `out/jail_env_probe.json`, `out/jail_runtime_results.json`, `out/jail_entitlements.json`, `out/jail_parity_summary.json`, plus exec-gate log captures `out/jail_logs_exec_gate_{relocated_true,file_probe_usage}_c7c4fdfb854b7ca0.log`.

## Blockers / risks
- Runtime observations are limited to the staged binaries and simple probes; broader coverage (other ops/filters) remains open.
- Entitlement-driven decode diffs are structural; filter/semantic alignment is still provisional until more tag/field2 mapping and runtime coverage exist.
- The jail runner may refuse to execute probes from the current staging location (`/private/tmp/...`) or may force containerized paths; this could make the jail path `blocked` until we restage probes to observed container directories.
- Current jail-run is `blocked` earlier than expected: even from the observed jail container `HOME`, executing a staged probe binary (`file_probe`) fails with `Operation not permitted`. Kernel log witnesses show this is a `process-exec*` deny for staged paths (see `out/jail_logs_exec_gate_file_probe_usage_c7c4fdfb854b7ca0.log`).

## Next steps
- Decide whether this witness is “done” (a clean `process-exec*` block) or whether we want a second, explicitly experimental witness that bundles the probes inside a sandboxed app.
- If continuing: build a bundled-probes app variant and extend `run_probes_jail.py` to use it for exec, then rerun the shared probe matrix and regenerate `out/jail_parity_summary.json`.
- If stopping: treat `EXEC_GATE_LOCATION_OR_WRITABLE_DENIED` + the `process-exec*` log witnesses as the experiment outcome and keep further entitlement-diff runtime work on the wrapper-applied path (`run_probes.py`) until a runnable jail witness exists.
