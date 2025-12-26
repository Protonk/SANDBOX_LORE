# Runtime Adversarial Suite – Research Report

## Purpose
Deliberately stress static↔runtime alignment for this host using adversarial SBPL profiles. This suite covers three families:
- Structural filesystem variants (file-read*/file-write*).
- VFS edge cases (`/tmp` vs `/private/tmp`).
- Non-filesystem ops (`mach-lookup` and `network-outbound`).
Outputs: expected/runtime matrices, mismatch summaries, and impact hooks to downgrade bedrock claims if mismatches appear.

## Baseline & scope
- World: `world_id sonoma-14.4.1-23E224-arm64-dyld-2c0602c5` (`book/world/sonoma-14.4.1-23E224-arm64/world-baseline.json`).
- Harness: `book.api.runtime_tools.harness.runner.run_matrix` + runtime-checks shims; file probes run via `sandbox_runner` + `file_probe` so each scenario applies exactly once inside a fresh worker; compile/decode via `book.api.profile_tools` and `book.api.profile_tools.decoder`.
- Profiles: `struct_flat`, `struct_nested` (structural variants); `path_edges` + `path_alias` (path/literal edge stress + `/tmp` alias witness); `mach_simple_allow`, `mach_simple_variants`, `mach_local_literal`, `mach_local_regex` (mach-lookup variants); `net_outbound_allow`, `net_outbound_deny`, `flow_divert_require_all_tcp` (network-outbound variants including the flow-divert require-all triple). Custom SBPL only; no platform blobs.
- Outputs live in `sb/`, `sb/build/`, and `out/`.

## Status update (apply-gated run)
- Latest refresh is apply-gated: `sandbox_init` returns `EPERM` across the adversarial profiles, so decision-stage outcomes are not available in the current `out/runtime_results.json` (failure_stage=`apply`).
- The path-alias (`path_alias`) and flow-divert require-all (`flow_divert_require_all_tcp`) profiles were added in this run, but their probes are also apply-gated; treat them as attempted/blocked until the apply gate is cleared.
- `out/apply_preflight.json` captures a dedicated apply-only attempt plus runner entitlements and parent-chain context; this is a blocked-evidence gate check, not a policy decision.
- `out/apply_preflight.json` now also records launchctl procinfo output, libproc parent-chain data, and a low-noise environment fingerprint (log/procinfo/proc_pidpath probes). Treat these as attribution inputs, not as sandbox semantics.
- Current host context: `launchctl procinfo` returns “requires root privileges,” and `log show` reports “Cannot run while sandboxed”; parent-chain attribution is therefore sourced from libproc only.

## Families and findings

### Structural variants (struct_flat / struct_nested)
- Static intent: distinguish allowed vs denied paths under a simple subpath policy rooted at `/tmp/runtime-adv/struct/ok`.
- Runtime: apply-gated in the latest run (no decision-stage outcomes recorded).
- Conclusion: structural intent remains, but runtime outcomes are blocked until apply-gate clears.

### VFS edge cases (path_edges)
- Static intent: allow literal `/tmp/runtime-adv/edges/a` and subpath `/tmp/runtime-adv/edges/okdir/*`, deny `/private/tmp/runtime-adv/edges/a` and the `..` literal to catch traversal. Decoder predicts allows on `/tmp/...` probes via literal/subpath filters.
- Runtime: apply-gated in the latest run; no decision-stage outcomes recorded. Canonicalization evidence remains anchored in `book/experiments/vfs-canonicalization/Report.md` (mapped-but-partial).

### Mach families (mach_simple_* / mach_local_*)
- Static intent: allow `mach-lookup` for `com.apple.cfprefsd.agent` only; profiles use literal vs regex and global-name vs local-name encodings, but aim for the same allow/deny surface (explicit deny on a bogus service).
- Runtime: apply-gated in the latest run; no decision-stage outcomes recorded.
- Conclusion: mach runtime evidence is currently blocked; rerun once apply-gate clears.

### Network family (net_outbound_allow / net_outbound_deny)
- Static intent: exercise `network-outbound` under deny-default profiles where the only policy difference is the presence/absence of an allow rule for outbound network.
- Runtime: apply-gated in the latest run; no decision-stage outcomes recorded.

## Evidence & artifacts
- SBPL sources: `book/experiments/runtime-adversarial/sb/*.sb`.
- Expected/runtime outputs: `book/experiments/runtime-adversarial/out/{expected_matrix.json,runtime_results.json,mismatch_summary.json,impact_map.json}`.
- Apply preflight: `book/experiments/runtime-adversarial/out/apply_preflight.json` (runner entitlements + apply markers + parent chain).
- Historical runtime events: `book/experiments/runtime-adversarial/out/historical_runtime_events.json` (only refreshed when a decision-stage run succeeds).
- Mapping stub: `book/graph/mappings/runtime/adversarial_summary.json` (world-level counts).
- Guardrails: `book/tests/test_runtime_adversarial.py`, `book/tests/test_network_outbound_guardrail.py`, plus dyld slice manifest/checker `book/graph/mappings/dyld-libs/{manifest.json,check_manifest.py}` enforced by `book/tests/test_dyld_libs_manifest.py`.
- Runtime-backed ops: `book/graph/mappings/vocab/ops_coverage.json` marks `file-read*`, `file-write*`, `mach-lookup`, and `network-outbound` as having runtime evidence via runtime-checks and runtime-adversarial families; use it to decide when new probes are needed for other ops.

## Claims and limits
- Covered ops/shapes: adversarial probes cover file-read*/file-write* (bucket-4/bucket-5 filesystem profiles and structural/metafilter variants), `mach-lookup` (global-name and local-name, literal and regex, simple vs nested forms), and `network-outbound` (loopback TCP via nc under deny-default + startup shims), plus a flow-divert require-all triple profile.
- Static↔runtime alignment: current run is apply-gated, so decision-stage alignment is not observable in the latest outputs. Treat earlier allow/deny conclusions as stale until apply-gate clears and the harness is rerun.
- Bounded mismatch: `/tmp` → `/private/tmp` canonicalization remains a known boundary from the focused VFS canonicalization experiment; it is not treated as a decoder bug.
- Scope of claims: do not treat adversarial runtime results as bedrock while apply-gated; keep `runtime_evidence` usage conservative and rely on static IR + explicit blocked status.

## Network-outbound runtime confirmation
This family targets the `network-outbound` operation to confirm mapped behavior on this host via a clean runtime allow/deny split. Early attempts that sandboxed Python hit startup/file-access noise; the final design deliberately avoids sandboxing Python and pins the client to `/usr/bin/nc`.
Current run note: the latest harness execution is apply-gated (`sandbox_init` EPERM), so decision-stage allow/deny outcomes are not observable in the current outputs; treat the details below as design intent until a clean apply path is available.

### Canonical scenario
- **Host**: `world_id sonoma-14.4.1-23E224-arm64-dyld-2c0602c5` (this scenario is scoped to this world).
- **Client**: `/usr/bin/nc -z -w 2`.
- **Profiles**: deny default plus startup shims (`iokit-open`, `mach* sysctl-read`, `file-ioctl`, `file-read-metadata`, `file-read-data` over `/`, `/System`, `/usr`, `/Library`, `/private`, `/dev`), `system-socket`, and `process-exec` pinned to `/usr/bin/nc`.
  - `sb/net_outbound_allow.sb`: includes `allow network-outbound …`.
  - `sb/net_outbound_deny.sb`: identical except it omits `network-outbound`.
- **Topology**: two loopback targets (as emitted in `out/expected_matrix.json`, e.g., `127.0.0.1:<port1>` and `127.0.0.1:<port2>`). The harness spins up listeners on both and runs `/usr/bin/nc` under each profile against both targets.

### Manual control (sandbox-exec)
Before refactoring the harness, a bespoke SBPL under `sandbox-exec -f … /usr/bin/nc 127.0.0.1 <port>` with deny-default, startup shims, `system-socket`, and a localhost `network-outbound` rule showed: allow profile → successful TCP connect; deny profile → denied connect. The harness design mirrors this control, proving Sonoma + Seatbelt + `network-outbound` + `nc` works when Python is not sandboxed.

### Results and propagation
- Runtime behavior: current run is apply-gated; decision-stage outcomes are not observable in the latest outputs.
- IR updates: runtime mappings and coverage have been refreshed from the latest cut, but mismatches should be treated as apply-gated until a clean run restores decision-stage evidence.

### Guardrail test
- Structural: `book/tests/test_network_outbound_guardrail.py` loads `sb/net_outbound_allow.sb` and `sb/net_outbound_deny.sb` and asserts they are identical except for the `network-outbound` rule.
- Behavioral: the same test checks `adv:net_outbound_allow*` probes all yield allow and `adv:net_outbound_deny*` probes all yield deny in `out/runtime_results.json`.
- Intent: prevents reintroducing sandboxed Python or profile shape drift that would blur the `network-outbound` decision between harness noise and PolicyGraph behavior.

### Status and adjacent work
- `network-outbound` is confirmed on this world by runtime via the canonical scenario and marked runtime-backed in coverage and CARTON.
- Planned but non-blocking: add a small variant (alternate port or IPv6 loopback) using the same client/profiles; add a “negative harness” profile (remove `system-socket`) expected to fail as a harness/startup error rather than a policy decision.
- Remaining runtime divergences: `/tmp`→`/private/tmp` VFS canonicalization in filesystem probes; see `book/experiments/vfs-canonicalization/Report.md` for the focused canonicalization family and guardrails (mapped-but-partial).

## Next steps
- Extend network coverage with a small variant (alternate port or IPv6 loopback) using the same client/profiles; add a “negative harness” profile (remove `system-socket`) expected to fail as a harness/startup error rather than a policy decision.
- Keep `path_edges` behavior aligned with `book/experiments/vfs-canonicalization/Report.md` so VFS canonicalization remains explicitly modeled and bounded.
- Extend families (header/format toggles, field2/tag ambiguity, additional non-filesystem ops) once current cases are stable; wire additional validation selectors if promotion to shared runtime mappings is desired.
- When apply-gated, run `book/experiments/runtime-adversarial/run_via_launchctl.py` to execute the harness from a launchd job that requires a clean preflight (abort if `sandbox_init` is already blocked).
