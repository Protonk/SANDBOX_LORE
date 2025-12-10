# Entitlement Diff – Research Report

## Purpose
Trace how selected entitlements alter compiled sandbox profiles and the resulting allow/deny behavior. Ground the entitlement concept in concrete profile/filter/parameter changes and, where possible, runtime probes.

## Baseline & scope
- World: sonoma-14.4.1-23E224-arm64-dyld-2c0602c5 (SIP enabled).
- Tooling: `entitlement_sample` binaries, App Sandbox stubs under `sb/`, `build_profiles.py` to inline/compile, `diff_profiles.py` to decode/diff, `run_probes.py` for runtime attempts.
- Entitlements: baseline has only app-sandbox; variant enables `com.apple.security.network.server` and a single mach-lookup global-name (`com.apple.cfprefsd.agent`).

## Deliverables / expected outcomes
- Minimal C sample and signed variants (`entitlement_sample`, `entitlement_sample_unsigned`) with extracted entitlements recorded in `out/*.entitlements.plist`.
- A workable method (still to be completed) for deriving per-entitlement App Sandbox profiles suitable for decoding and comparison.
- Planned diffs that connect entitlement keys → SBPL parameters/filters → compiled graph deltas → runtime allow/deny behavior.
- A short manifest tying binaries, profiles, decoded diffs, and probe logs together for this host.

## Plan & execution log
### Completed
- Sample program built (`entitlement_sample`) and unsigned variant captured with entitlements in `out/entitlement_sample*.entitlements.plist`.
- App Sandbox stubs derived from `book/profiles/textedit/application.sb` with pinned params/entitlements (`sb/appsandbox-*.sb`); `build_profiles.py` expands/compiles to `sb/build/*.expanded.sb` and `.sb.bin`.
- Decoded both blobs and wrote structural deltas to `out/profile_diffs.json` (ops present via op_table indices, literal adds/removals, literal_refs deltas, tag deltas) alongside raw decodes in `out/decoded_profiles.json`.
- Runtime probes via `book/api/SBPL-wrapper/wrapper --blob` with staged binaries under `/private/tmp/entitlement-diff/app_bundle/`:
  - baseline (app sandbox only): `entitlement_sample` bind denied (`bind: Operation not permitted`), `mach_probe com.apple.cfprefsd.agent` allowed.
  - network_mach (network.server + mach allowlist): bind allowed, mach-lookup allowed.
  Results recorded in `out/runtime_results.json`.

### Planned
- Show how specific entitlements change compiled profiles and filters/parameters, and how those changes affect runtime behavior. Produce diffs that connect entitlements → SBPL parameters/filters → compiled graph → allow/deny behavior.
  
  
  - Pick a small set of entitlements that are known to toggle sandbox capabilities (e.g., network server/client, mach-lookup exceptions, file access).
  - Build two or three binaries (unsigned vs signed with entitlement; optional alternate entitlement) using minimal code.
  - Outputs: extracted entitlements, compiled profiles, decoded filter/param deltas, and runtime probe logs where feasible.
  
  
  1) **Select entitlements**
     - Choose 2–3 candidate keys (e.g., `com.apple.security.network.server`, a mach-lookup entitlement, a file-access entitlement if available).
  
  2) **Build variants**
     - Create a tiny C program (e.g., prints entitlements and opens a test resource).
     - Sign variants with/without each entitlement (or ad-hoc where possible).
  
  3) **Compile and decode profiles**
     - Extract compiled profiles associated with each variant (via libsandbox compile or system tooling).
     - Decode with `profile_ingestion.py` and diff filters/parameters to show entitlement-driven changes.
  
  4) **Runtime probes (if allowed)**
     - Run simple probes (file/network/mach) under each variant and log allow/deny results. Use `book/api/SBPL-wrapper/wrapper` (SBPL or blob) instead of `sandbox-exec` where possible. Note if SIP/TCC block runtime on this host; rerun in a permissive environment if needed.
  
  5) **Summarize deltas**
     - Produce a short manifest showing entitlement → filter/param changes → observed behavior, with OS/build metadata.
  
  Status: binaries and entitlements captured; need a method to derive/apply sandbox profiles that reflect the entitlements (e.g., App Sandbox template) before runtime probes. Wrapper is available once profiles are derived.
  
  
  - At least one entitlement with a clear profile/filter delta demonstrated across signed variants.
  - Decoded diffs and (if possible) runtime logs linked in a manifest.
  - Notes on environment constraints (e.g., SIP, signing requirements).

## Evidence & artifacts
- Source and build scaffolding for `entitlement_sample` under this experiment directory; extracted entitlements in `out/entitlement_sample*.entitlements.plist`.
- App Sandbox stubs and compiled outputs in `sb/` and `sb/build/` (expanded SBPL + blobs); build helper `build_profiles.py`.
- Decodes and structural diffs in `out/decoded_profiles.json` and `out/profile_diffs.json` (includes literal_refs and tag_literal_refs); manifest recorded in `out/manifest.json`.
- Runtime results in `out/runtime_results.json` (baseline: network bind/outbound denied, mach allowed, container file read/write allowed; network_mach: bind allowed, mach allowed, file read/write allowed, outbound `nc` to localhost still denied).

## Blockers / risks
- Runtime observations are limited to the staged binaries and simple probes; broader coverage (other ops/filters) remains open.
- Entitlement-driven decode diffs are structural; filter/semantic alignment is still provisional until more tag/field2 mapping and runtime coverage exist.

## Next steps
- Extend runtime probes to additional operations (e.g., mach-register, outbound network variants) if we add matching helpers.
- Refine filter-level interpretation as tag/field2 mapping improves; align observed tag_literal_refs with expected entitlement-driven rules.
- Keep the entitlement manifest format stable and track any further runtime scenarios in `out/runtime_results.json`; consider mapping op-table deltas to vocab IDs once alignment is available.
