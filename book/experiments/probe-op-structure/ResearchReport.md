# Probe Op Structure – Research Report (Sonoma / macOS 14.4.1)

## Purpose

Design and run richer SBPL probes to surface filter-specific nodes and `field2` values by varying operations, filters, and metafilters. The goal is to overcome the “generic path/name dominance” seen in minimal profiles and extract clearer `field2` ↔ filter-ID signals and structural patterns that other experiments can reuse.

## Baseline and scope

- Host: macOS 14.4.1 (23E224), Apple Silicon, SIP enabled (shared baseline).
- Vocab artifacts: `book/graph/concepts/validation/out/vocab/ops.json` (196 entries, status: ok) and `filters.json` (93 entries, status: ok).
- Related work:
  - `field2-filters`: tiny single-filter profiles mostly surfaced generic path/name `field2` values.
  - `op-table-operation`: bucket behavior for small operation sets.
  - `node-layout`: structural patterns for nodes/tags with various filter shapes.

## What we tried and why it fell short

We implemented a first probe matrix (file require-all/any mixes, mach global/local, network socket filters, iokit class/property, and mixed combos) and compiled them via `libsandbox`. Decoding with vocab padding yielded:

- `field2` values remained dominated by low, generic IDs: `global-name` (5), `local-name` (6), `ipc-posix-name` (4), `file-mode` (3), `remote` (8), regardless of the intended filter mix.
- The network probe surfaced `remote` (8); mach variants surfaced {5,6}; file variants surfaced {3,4} or {5,6}. Mixed profiles showed the same low IDs.
- The “all-combo” profile (`v8`) failed the heuristic decoder (node_count 0), likely due to literal-start detection; richer slicing would be needed there.

Discovery: even with more structure, short op-tables and generic path/name scaffolding mask filter-specific `field2` signals. Graph walks from op-table entries alone tend to hit shared path/name filters instead of the specific filter nodes we’re trying to isolate. This mirrors the earlier field2 experiment and suggests we need better slicing and literal-anchored traversal.

## Plan (revised)

1. Improve slicing/decoding for richer profiles (better literal/pool detection; fallback to segment-aware slicing to avoid node_count=0).
2. Anchor traversal on literals: scan decoded literals for strong anchors (paths, mach names, iokit classes), then map nodes referencing those literals to their `field2` values to isolate filter-specific nodes.
3. Design profiles with disjoint anchor sets per filter to make literal→filter mapping unambiguous.
4. Use multi-op profiles where different filter families live on different ops to separate paths during traversal.
5. Triangulate with system profiles (clear anchors) to confirm mappings.
6. Cross-op consistency: verify inferred `field2` per filter across ops that share it.
7. Guardrails: once mappings emerge, add a checker that locates anchor literals in probe blobs and asserts expected `field2` values.
8. Document evidence tiers: maintain a table of `field2`→filter mappings with provenance and mark uncertain cases.

## Current status

- Experiment scaffold and initial probes are in place; early decoding confirms the masking problem described above.
- Revised plan focuses on anchor-based traversal and improved slicing rather than adding more small probes.

## Expected outcomes

- Probes and analysis that surface filter-specific `field2` values beyond generic path/name scaffolding.
- Provisional `field2` ↔ filter-ID mappings supported by anchor evidence and system-profile cross-checks.
- Structural notes (tags/branch shapes) that correlate with particular filters/metafilters.
- Guardrail checks for key mappings once established.

## Expected outcomes

- A set of richer probe profiles that surface filter-specific `field2` values beyond the generic path/name scaffolding.
- Provisional mappings of `field2` ↔ filter-ID supported by multiple probes.
- Structural notes (tags/branch shapes) that correlate with particular filters/metafilters.
- Reusable guardrails for key mappings.
