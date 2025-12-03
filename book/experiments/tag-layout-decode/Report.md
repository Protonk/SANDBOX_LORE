# Tag Layout Decode – Research Report (Sonoma / macOS 14.4.1)

## Purpose
Map node tags that reference literal or regex pools to interpretable layouts (edge fields plus operand fields) using the current decoder and anchor hits. Produce a reusable map at `book/graph/mappings/tag_layouts/tag_layouts.json` for other tooling and book chapters.

## Baseline & scope
- Host: macOS 14.4.1 (23E224), Apple Silicon, SIP enabled (same baseline as other experiments).
- Inputs: canonical system profiles (`book/examples/extract_sbs/build/profiles/{airlock,bsd,sample}.sb.bin`), probe outputs from `probe-op-structure`, and shared vocab/op-table mappings in `book/graph/mappings/`.
- Tooling: `book.api.decoder` for profile decoding; anchor hints from `book/graph/mappings/anchors/anchor_field2_map.json`.
- Target artifact: `book/graph/mappings/tag_layouts/tag_layouts.json` (per-tag layout with operand interpretation and provenance).

## Deliverables / expected outcomes
- A per-tag layout map for literal/regex-bearing nodes with evidence trails.
  - Guardrail script/test that asserts expected literal/regex placements on reference blobs.
  - Updated Notes and Plan with any deviations or open questions.
- Deliverables: `Plan.md`, `Notes.md`, `ResearchReport.md` in this directory; `out/` folder for scratch JSON/histograms.
- Deliverables: `out/tag_histogram.json` (or similar) with tag → counts, literal/regex usage.
- Deliverables: draft `tag_layouts.json` (per-tag layout description) plus short notes on evidence.

## Plan & execution log
### Completed
- **Current status**
  - Experiment scaffolded (this report, Plan, Notes).
  - Baseline decode complete for canonical system profiles (`airlock`, `bsd`, `sample`); tag counts and literal counts recorded in `out/tag_histogram.json`. Decoder inputs: `book/examples/extract_sbs/build/profiles/{airlock,bsd}.sb.bin`, `book/examples/sb/build/sample.sb.bin`.
  - Sample literal-bearing nodes grouped by tag captured in `out/tag_literal_nodes.json` to support layout interpretation.
  - Best-effort tag layouts published at `book/graph/mappings/tag_layouts/tag_layouts.json` (record_size=12, edges fields[0..1], payload field[2] for literal-bearing tags 0,1,3,5,7,8,17,26,27,166). Decoder now prefers this mapping when present. Guardrail test added (`tests/test_mappings_guardrail.py`) to ensure the mapping persists.
- **1) Scope and setup**
  - Identified reference blobs: canonical system profiles (`airlock.sb.bin`, `bsd.sb.bin`, `sample.sb.bin`) and shared mappings needed for decoding.
  - Confirmed decoder path (`book.api.decoder`) and access to `book/graph/mappings/vocab` and `book/graph/mappings/op_table`.
- **2) Baseline decode and tag histogram**
  - Decoded reference blobs; captured node tag histograms, literal pool offsets, and basic section information in `out/tag_histogram.json`.
- **3) Tag layout reconstruction**
  - For tags that carry literal/regex operands, mapped field positions (edges vs payloads) using literal tables on canonical profiles and wrote initial layouts.
- **4) Synthesis and guardrails**
  - Finalized `book/graph/mappings/tag_layouts/tag_layouts.json` with per-tag field sizes, edge fields, and payload fields for literal-bearing tags, plus host metadata.
  - Added guardrail tests (`tests/test_mappings_guardrail.py`) that assert presence and basic shape of the tag layout mapping.
  - Updated `ResearchReport.md` and `Notes.md` to describe current layouts and how they are used by the decoder.

### Planned
- 1. Baseline decode and histogram of reference blobs to identify tags that carry literal/regex operands.
  2. Reconstruct per-tag field meanings (edges vs operands) using literal/regex tables and anchor hits.
  3. Synthesize a stable tag-layout map and add guardrail checks against reference blobs.
- **1) Scope and setup**
  - Make host baseline (OS/build, SIP, decoder version) explicit in `ResearchReport.md` if tag layouts are extended or revised.
- **2) Baseline decode and tag histogram**
  - Refine notes on which tags show literal or regex indices and any sentinel/padding patterns as decoding improves.
- **3) Tag layout reconstruction**
  - Use anchors from `probe-op-structure` and shared vocab/op-table mappings to refine tag layouts and detect reused structures across operations.
- **4) Synthesis and guardrails**
  - Revisit layouts if new tags or operand types surface in future experiments.
  Stop condition: tag layouts for literal/regex-bearing nodes validated across reference blobs and probes; reusable map committed; guardrail in place.

## Evidence & artifacts
- Reference blobs `airlock.sb.bin`, `bsd.sb.bin`, and `sample.sb.bin` decoded via `book.api.decoder`.
- `book/experiments/tag-layout-decode/out/tag_histogram.json` with tag counts and literal usage across these profiles.
- `book/experiments/tag-layout-decode/out/tag_literal_nodes.json` capturing sample literal-bearing nodes grouped by tag.
- Published tag-layout map `book/graph/mappings/tag_layouts/tag_layouts.json` plus associated guardrail tests in `tests/test_mappings_guardrail.py`.

## Blockers / risks
- Tag layouts are currently defined for a subset of literal/regex-bearing tags; additional tags or operand types in future profiles may require revisiting or extending the map.
- Layout interpretations rely on the current decoder and literal-table heuristics; mistakes there could propagate into downstream experiments that consume `tag_layouts.json`.

## Next steps
- Use additional probes and system profiles (including anchor-heavy cases from `probe-op-structure`) to refine or extend per-tag layouts as needed.
- Update `tag_layouts.json` and guardrails when new tags or operand patterns are confirmed, keeping host/build metadata and provenance up to date.
