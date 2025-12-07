# Runtime Adversarial Suite – Research Report (Sonoma 14.4.1, arm64, SIP on)

## Purpose
Deliberately stress static↔runtime alignment for this host using adversarial SBPL profiles. Phase 1 covers structural variants and path/literal edges; mach-lookup variants extend coverage to a non-filesystem op. Outputs: expected/runtime matrices, mismatch summaries, and impact hooks to downgrade bedrock claims if mismatches appear.

## Baseline & scope
- World: `sonoma-14.4.1-23E224-arm64` (`book/world/sonoma-14.4.1-23E224-arm64/world-baseline.json`).
- Harness: `book.api.golden_runner.run_expected_matrix` + runtime-checks shims; compile/decode via `book.api.sbpl_compile` and `book.api.decoder`.
- Profiles: `struct_flat`, `struct_nested` (structural variants); `path_edges` (path/literal edge stress); `mach_simple_allow`, `mach_simple_variants` (mach-lookup variants). Custom SBPL only; no platform blobs.
- Outputs live in `sb/`, `sb/build/`, and `out/`.

## Current status
- Scaffolded experiment with SBPL sources, build directory, and driver script `run_adversarial.py`.
- Expected/runtime/mismatch/impact JSON schemas defined; guardrail test added.
- Structural variants round-trip (allow/deny probes match); path/literal edge family yields runtime denies on `/tmp` allow probes, categorized as `path_normalization` and annotated in `impact_map.json`.
- Mach family added (allow specific global-name via literal vs regex/nested); see case study below for runtime outcomes.
- Artifacts seeded via `run_adversarial.py`; rerun to refresh after edits.

## Case study – path_edges
- Static intent: allow literal `/tmp/runtime-adv/edges/a` and subpath `/tmp/runtime-adv/edges/okdir/*`, deny `/private/tmp/runtime-adv/edges/a` and the `..` literal to catch traversal. Decoder predicts allows on `/tmp/...` probes via literal/subpath filters.
- Runtime: both `/tmp/...` allow probes return deny with `EPERM` (open target) despite static allow; `/private/tmp` deny and `..` deny align.
- Interpretation: mismatch attributed to VFS canonicalization (`/tmp` → `/private/tmp`) prior to PolicyGraph evaluation rather than tag/layout divergence. Treated as out-of-scope for static IR; captured in `impact_map.json` with `out_of_scope:VFS_canonicalization` and no downgrade to bedrock mappings.

## Case study – mach_variants
- Static intent: allow `mach-lookup` for `com.apple.cfprefsd.agent` only; `mach_simple_variants` uses regex/nesting but aims for the same allow/deny surface (explicit deny on a bogus service).
- Runtime: with baseline allows added for process exec and system reads, both profiles now allow the target service and deny the bogus one; no mismatches recorded. `impact_map.json` marks these expectation_ids as reinforcing the mach-lookup vocab/op-table assumptions (op ID 96).
- Conclusion: mach runtime coverage is now `ok` for this allow/deny pair; further mach/XPC variants can extend coverage.

## Evidence & artifacts
- SBPL sources: `book/experiments/runtime-adversarial/sb/*.sb`.
- Expected/runtime outputs: `book/experiments/runtime-adversarial/out/{expected_matrix.json,runtime_results.json,mismatch_summary.json,impact_map.json}`.
- Mapping stub: `book/graph/mappings/runtime/adversarial_summary.json` (world-level counts).
- Guardrails: `book/tests/test_runtime_adversarial.py` plus dyld slice manifest/checker `book/graph/mappings/dyld-libs/{manifest.json,check_manifest.py}` enforced by `book/tests/test_dyld_libs_manifest.py`.

## Next steps
- Run `run_adversarial.py` to regenerate artifacts; inspect `mismatch_summary.json` and annotate `impact_map.json` for any mismatches.
- Extend families (header/format toggles, field2/tag ambiguity, additional non-filesystem ops) once current cases are stable.
- Wire a validation selector if promotion to shared runtime mappings is desired.
