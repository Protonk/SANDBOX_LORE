# Runtime Adversarial Suite – Research Report (Sonoma 14.4.1, arm64, SIP on)

## Purpose
Deliberately stress static↔runtime alignment for this host using adversarial SBPL profiles. Phase 1 targets two families: structurally distinct-but-equivalent graphs and path/literal normalization edges. Outputs: expected/runtime matrices, mismatch summaries, and impact hooks to downgrade bedrock claims if mismatches appear.

## Baseline & scope
- World: `sonoma-14.4.1-23E224-arm64` (`book/world/sonoma-14.4.1-23E224-arm64/world-baseline.json`).
- Harness: `book.api.golden_runner.run_expected_matrix` + runtime-checks shims; compile/decode via `book.api.sbpl_compile` and `book.api.decoder`.
- Profiles: `struct_flat`, `struct_nested` (structural variants), `path_edges` (path/literal edge stress). Custom SBPL only; no platform blobs.
- Outputs live in `sb/`, `sb/build/`, and `out/`.

## Current status
- Scaffolded experiment with SBPL sources, build directory, and driver script `run_adversarial.py`.
- Expected/runtime/mismatch/impact JSON schemas defined; guardrail test added.
- Structural variants now round-trip (allow/deny probes match); path/literal edge family currently shows runtime denies on `/tmp` allow probes (categorized as `path_normalization`, annotated in `impact_map.json`).
- Artifacts seeded via `run_adversarial.py`; rerun to refresh after edits.

## Evidence & artifacts
- SBPL sources: `book/experiments/runtime-adversarial/sb/*.sb`.
- Expected/runtime outputs: `book/experiments/runtime-adversarial/out/{expected_matrix.json,runtime_results.json,mismatch_summary.json,impact_map.json}`.
- Mapping stub: `book/graph/mappings/runtime/adversarial_summary.json` (world-level counts).
- Guardrail: `book/tests/test_runtime_adversarial.py`.

## Next steps
- Run `run_adversarial.py` to regenerate artifacts; inspect `mismatch_summary.json` and annotate `impact_map.json` for any mismatches.
- Extend families (header/format toggles, field2/tag ambiguity, non-filesystem ops) once Phase 1 is stable.
- Wire a validation selector if promotion to shared runtime mappings is desired.
