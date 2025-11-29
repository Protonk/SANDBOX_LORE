# Probe Op Structure Experiment (Sonoma host)

Goal: design and run a set of SBPL probes with richer, varied structure to extract clearer mappings between operations, filters (and their `field2` encodings), and op-table behavior. This experiment should complement the field2-focused work by using more complex profiles (multiple filters, layered ops) to surface filter-specific nodes beyond the generic path/name scaffolding.

---

## 1) Scope and setup

- [ ] Record host baseline (OS/build, kernel, SIP) in `ResearchReport.md`.
- [ ] Confirm vocab artifacts (`graph/mappings/vocab/ops.json`, `filters.json`) are `status: ok`.
- [ ] Identify prior experiments to reuse/compare: `field2-filters`, `op-table-operation`, `node-layout`.

Deliverables:
- `Plan.md`, `Notes.md`, `ResearchReport.md` in this directory.
- A structured probe matrix describing intended SBPL variants.

## 1.5) Per-tag inventory (sanity pass)

- [ ] Group decoded nodes by tag across a few profiles (simple probes + system profiles).
- [ ] Record total bytes per tag, candidate minimal strides (common divisors), and remainders.
- [ ] Keep stride scans as coarse slicing sanity (front vs tail), not as final layouts.

Deliverables:
- Notes on tag byte counts/stride candidates in `Notes.md`; brief summary in `ResearchReport.md`.

## 2) Improve slicing/decoding

- [ ] Add segment-aware slicing fallback for complex profiles to avoid node_count=0 (e.g., use op_table length from vocab; literal/pool detection with a stronger heuristic).
- [ ] Keep the heuristic decoder but record when fallback is used.

Deliverables:
- Updated helper script(s) for slicing/decoding richer profiles; note usage in `Notes.md`.

## 3) Anchor-based traversal

- [ ] Scan decoded literals/strings for strong anchors (paths, mach names, iokit classes) per profile.
- [ ] Map anchor literals to nodes (`field2`, tag, offsets), not just op-table entry walks.
- [ ] Prefer anchors that are unique per filter to reduce ambiguity.
  - Status: anchors now resolve to literal offsets; decoded `literal_refs` yield node indices for simple probes (e.g., `/tmp/foo` in `v1_file_require_any` → nodes [16,22,30]). Still heuristic; needs richer tag decoding.

Deliverables:
- JSON or notes tying anchor literals → node indices → `field2` → inferred filter.

## 4) Probe design (anchor-aware)

- [ ] Define profiles where each filter has a disjoint anchor (e.g., unique paths, mach names, iokit class names).
- [ ] Include multi-op profiles where different filter families live on different ops to separate traversal paths.

Deliverables:
- Updated probe matrix in `Notes.md` reflecting anchor choices.

## 5) Compilation and decoding

- [ ] Author/adjust SBPL per the anchor-aware matrix; compile via `libsandbox` to `sb/build/*.sb.bin`.
- [ ] Decode with updated slicing; collect both op-table walks and anchor-based node hits.

Deliverables:
- `sb/` sources and compiled blobs; updated summaries including anchor-based findings.

## 6) Analysis and mapping

- [ ] Compare anchor-derived `field2` values across probes to isolate filter-specific IDs.
- [ ] Cross-op consistency checks for shared filters using anchor evidence.
- [ ] Triangulate with system profiles (clear anchors) where possible.
- [ ] **Tag-specific layout hypotheses:** propose per-tag record sizes/field positions; evaluate via edge in-bounds rates and literal/regex operand plausibility. Capture candidate layouts and evidence in `Notes.md`, summarize accepted/rejected in `ResearchReport.md`.
- [ ] **Literal/regex correlation:** use profiles that differ only in literal content/count to see which tag/field positions change; cross-check with system-profile anchors to validate operand slots.

Deliverables:
- Updated `ResearchReport.md` with provisional mappings, evidence tiers, and structural notes.

## 7) Guardrails and reuse

- [ ] Add a checker that locates anchor literals in probe blobs and asserts expected `field2` values once mappings stabilize.
- [ ] Document reuse for other experiments (field2 mapping, op-table alignment).

Deliverables:
- Guardrail script/test (when mappings are ready) and usage notes in `Notes.md`.

## 6) Guardrails and reuse

- [ ] Add a small assertion script/test to verify key mappings found here.
- [ ] Document how these probes can be reused by other experiments (field2 mapping, op-table alignment).

Deliverables:
- Guardrail script/test (if mappings emerge), plus usage notes in `Notes.md`.
