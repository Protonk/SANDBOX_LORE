# Field2 ↔ Filter Mapping Experiment (Sonoma host)

Goal: map decoder `field2` values to Filter IDs using the harvested filter vocabulary and targeted SBPL probes, then validate consistency across operations and profiles.

---

## 1) Scope and setup

**Done**

- Host baseline (OS/build, kernel, SIP) and canonical blobs recorded in `ResearchReport.md`.
- Vocab artifacts (`book/graph/mappings/vocab/filters.json`, `ops.json`) confirmed `status: ok` (93 filters, 196 ops).
- Canonical blobs for cross-check identified and used: `book/examples/extract_sbs/build/profiles/airlock.sb.bin`, `bsd.sb.bin`, `sample.sb.bin`.

**Upcoming**

- Keep baseline/version notes updated if the host or vocab artifacts change.
- Continue to carry the third node slot explicitly as `filter_arg_raw` with derived `field2_hi/field2_lo`; do not coerce high/unknown values into the existing filter vocabulary.

Deliverables:
- `Plan.md`, `Notes.md`, `ResearchReport.md` in this directory.
- A small helper script to collect `field2` values from decoded profiles.

## 2) Baseline inventory

**Done**

- Decoded canonical blobs and tallied unique `field2` values; baseline histograms recorded in `ResearchReport.md` and `Notes.md`. Refreshed the census to include hi/lo splits and per-tag counts, and pulled in mixed probe-op-structure builds to keep flow-divert and other richer shapes in view.
- Confirmed that many `field2` values align directly with filter vocab IDs (e.g., path/socket/iokit filters in `bsd` and `sample`), with high unknowns in `airlock`.

**Upcoming**

- Refine per-tag/per-op inventories using newer decoder layouts if needed.

Deliverables:
- Intermediate JSON/notes summarizing `field2` histograms and per-op reachable values.

## 3) Synthetic single-filter probes

**Done**

- Authored single-filter SBPL variants (subpath, literal, global-name, local-name, vnode-type, socket-domain, iokit-registry-entry-class, require-any mixtures) and compiled them under `sb/build/`; added probe-op-structure mixed-operation builds to keep the flow-divert 2560 signal available for comparison.
- Decoded each variant and recorded `field2` values; synthesized into `out/field2_inventory.json`.

**Upcoming**

- Design additional probes that reduce or alter generic path/name scaffolding (e.g., richer operations or more complex metafilters) to surface filter-specific `field2` values; keep richer network shapes when chasing flow-divert (simplified profiles collapsed field2 to low IDs and lost 2560; richer mixes like v4/v7 retain 2560). Treat hi/lo views as diagnostic only until kernel bitfields are known.

Deliverables:
- `sb/` variants + compiled blobs under `sb/build/`.
- Notes mapping filter name → observed `field2` value(s) with provenance.

## 4) Cross-op consistency checks

**Done (initial)**

- Checked that low `field2` IDs corresponding to path/name filters (0,1,3,4,5,6,7,8) behave consistently across system profiles and synthetic probes.
- Confirmed that system profiles (`bsd`, `sample`) reinforce the mapping for common filters (preference-domain, right-name, iokit-*, path/socket).

**Upcoming**

- Perform focused cross-op checks for less common filters once better probes or anchors are available; chase the flow-divert-specific field2 (2560) using richer network mixes, and any other high/unknown values by varying operations. Simplified dtracehelper/posix_spawn probes yielded only low IDs, so full-profile context may be required; adding mach to the mimic still did not surface high IDs. Use graph shape/position as the primary classifier, with `field2_hi/lo` treated as auxiliary evidence only.
- Flag and investigate any inconsistencies that appear as decoding improves.

Deliverables:
- Table of filter → `field2` with cross-op status (consistent/inconsistent).

## 5) System profile cross-check

**Done (baseline)**

- Inspected curated system profiles where literals strongly indicate filter type (paths, mach names, iokit properties) and confirmed that `field2` IDs match vocab entries where known.

**Upcoming**

- Use anchor mappings and updated tag layouts to deepen system-profile cross-checks, especially for high, currently-unknown `field2` values in `airlock` and the `bsd` tail (e.g., 170/174/115/109/16660 tied to dtracehelper/posix_spawn literals that did not reappear in isolated probes). Track `(tag, field2_hi, field2_lo)` distributions for these cases without assigning semantics yet.

Deliverables:
- Notes tying system-profile nodes to the inferred mapping.

## 6) Synthesis and guardrails

**Done (partial)**

- Summarized current understanding of `field2` behavior (generic path/name dominance, confirmed mappings for common filters, persistence of unknowns) in `ResearchReport.md` and `Notes.md`.
- Regenerated `out/field2_inventory.json` using shared tag layouts and anchor/filter mappings to keep inventories aligned with the global IR.

**Upcoming**

- Distill a stable `field2` ↔ filter-ID table for a small, high-confidence subset of filters; attempt to promote flow-divert-related values and high system-profile values only once additional probes and/or Sandbox.kext bitfields confirm them.
- Add a guardrail test/script that checks these mappings against synthetic profiles once the semantic layer is better understood; for now, keep high/unknown values in an “unknown-arg” bucket.
- Extend `ResearchReport.md` with any newly established mappings and explicit open questions, noting where conclusions rely on hi/lo heuristics versus kernel evidence.

Deliverables:
- Updated `ResearchReport.md` and `Notes.md`.
- Guardrail test/script to prevent regressions.
