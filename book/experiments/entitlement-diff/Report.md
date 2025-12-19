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
- Implemented the EntitlementJail-based runner (`run_probes_jail.py`) and executed an env-probe + exec-smoke run:
  - Observed jail environment: `HOME=/Users/achyland/Library/Containers/com.yourteam.entitlement-jail/Data` (see `out/jail_env_probe.json`).
  - Exec-smoke blocked: staged `file_probe` could not be executed under the jail (`rc=126`, `Operation not permitted`), so the full jail matrix is currently `blocked` (see `out/jail_runtime_results.json`).
  - Stage discovery matrix (see `out/jail_env_probe.json`) indicates:
    - `stat`: repo checkout, `/tmp`, and stage root are visible.
    - `open`: stage-root file read succeeds, but reading from repo checkout and `/tmp` fails under the jail.
    - `exec`: executing `file_probe` fails with `Operation not permitted` across repo checkout, `/tmp`, and stage root.

### Planned
- Add an “App Sandbox parent runner” path using `book/tools/entitlement/EntitlementJail.app`, then rerun the existing probe matrix to cross-check wrapper-applied behavior against jail-run behavior.

  1) **Wire up an env-probe skeleton (witness-shaped)**
     - Run three jail commands end-to-end: `/usr/bin/id -a`, `/usr/bin/env`, `/bin/pwd`.
     - Capture stdout/stderr/rc for each and write `out/jail_env_probe.json`.
     - Use the observed `HOME`/`TMPDIR`/`PWD` as evidence for later staging decisions (do not assume them).

  2) **Pick a single stage root and make it invariant**
     - Anchor on the jail-observed `HOME` and stage under `$HOME/jail_stage/entitlement-diff/<run_id>/`.
     - Host-side staging: mkdir stage root, copy probes, `chmod +x` staged binaries.
     - Every jail invocation uses `cwd=stage_root` to keep relative-path and `getcwd()` behavior stable.
     - Optionally clear `com.apple.quarantine` on staged copies if exec failures suggest quarantine/xattrs are in play.

  3) **Prove exec works before widening**
     - Execute one real probe from the stage root (e.g., `file_probe read <stage_root>/smoke.txt`).
     - If this fails, stop and record the failure crisply; do not continue to the full matrix.

  4) **Make “blocked” first-class (and ruthless)**
     - Each probe attempt must land in exactly one of: `executed`, `blocked`, `harness_error`.
     - `blocked` must carry: attempted command line, rc/errno (when available), stderr, a coarse reason code (e.g., `JAIL_EXEC_FAILED`, `JAIL_CWD_UNUSABLE`, `DYLD_LOAD_FAILED`), plus stage_root context (file existence/perms).
     - Never reinterpret “couldn’t run” as “denied”.

  5) **Run the canonical probe matrix under the jail**
     - Reuse the same probe IDs and argument vectors as `run_probes.py`.
     - Avoid plan drift by sharing the probe plan via `book/experiments/entitlement_diff_probe_plan.py` (both runners consume it).
     - Write results to `out/jail_runtime_results.json`.

  6) **Stage discovery mini-matrix**
     - Explicitly test whether the jail can read/exec from: repo checkout paths, `/tmp`, `/private/tmp`, and the chosen `$HOME` stage root.
     - Keep it small but conclusive (path × operation: `stat`, `open`, `exec`) and write it out as evidence (either embedded in `out/jail_env_probe.json` or as a separate artifact).

  7) **Capture entitlements/signing metadata as evidence**
     - Parent (EntitlementJail): TeamIdentifier/Identifier, entitlements blob, sha256.
     - Child variants: same, plus the staged path actually executed.
     - Write `out/jail_entitlements.json`.

  8) **Parity summary**
     - Compare normalized outcomes (allow/deny + errno/kr), but preserve raw evidence.
     - Separate `match` vs `mismatch` vs `incomparable` (blocked on either side).
     - Write `out/jail_parity_summary.json`.

## Evidence & artifacts
- Source and build scaffolding for `entitlement_sample` under this experiment directory; extracted entitlements in `out/entitlement_sample*.entitlements.plist`.
- App Sandbox stubs and compiled outputs in `sb/` and `sb/build/` (expanded SBPL + blobs); build helper `build_profiles.py`.
- Decodes and structural diffs in `out/decoded_profiles.json` and `out/profile_diffs.json` (includes literal_refs and tag_literal_refs); manifest recorded in `out/manifest.json`.
- Runtime results in `out/runtime_results.json` (baseline: network bind/outbound denied, mach allowed, container file read/write allowed; network_mach: bind allowed, mach allowed, file read/write allowed, outbound `nc` to localhost still denied).
- Jail-run witness artifacts: `out/jail_env_probe.json`, `out/jail_runtime_results.json`, `out/jail_entitlements.json`, and `out/jail_parity_summary.json`.

## Blockers / risks
- Runtime observations are limited to the staged binaries and simple probes; broader coverage (other ops/filters) remains open.
- Entitlement-driven decode diffs are structural; filter/semantic alignment is still provisional until more tag/field2 mapping and runtime coverage exist.
- The jail runner may refuse to execute probes from the current staging location (`/private/tmp/...`) or may force containerized paths; this could make the jail path `blocked` until we restage probes to observed container directories.
- Current jail-run is `blocked` earlier than expected: even from the observed jail container `HOME`, executing a staged probe binary (`file_probe`) fails with `Operation not permitted` (likely a `process-exec*`-adjacent gate, but the precise reason is not yet mapped here).

## Next steps
- Add the EntitlementJail runner (`run_probes_jail.py`), capture parent/child entitlements, and write `out/jail_runtime_results.json`.
- Compare jail-run vs wrapper-run results and write `out/jail_parity_summary.json`.
- Extend runtime probes to additional operations (e.g., mach-register, outbound network variants) if we add matching helpers.
- Refine filter-level interpretation as tag/field2 mapping improves; align observed tag_literal_refs with expected entitlement-driven rules.
- Keep the entitlement manifest format stable and track any further runtime scenarios in `out/runtime_results.json`; consider mapping op-table deltas to vocab IDs once alignment is available.
