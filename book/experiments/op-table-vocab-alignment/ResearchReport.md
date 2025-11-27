# Op-table ↔ Operation Vocabulary Alignment (Sonoma host)

## 1. Motivation and objectives

The substrate treats **Operation**, **Operation Pointer Table**, and **Operation Vocabulary Map** as tightly linked concepts:

- Each SBPL Operation (e.g., `file-read*`, `mach-lookup`, `network-outbound`) has a numeric Operation ID in compiled profiles.
- The Operation Pointer Table is an indirection from these IDs to entry nodes in the compiled PolicyGraph.
- The Operation Vocabulary Map is a versioned mapping from symbolic names to IDs and argument schemas for a given OS build.

Two existing experiments approach this structure from different angles:

- `book/experiments/node-layout/` establishes the basic compiled profile layout: headers, Operation Pointer Table, node region, and literal/regex pools, and observes non-uniform op-table patterns (e.g., `[6,…,5]`) without assigning them to specific Operations.
- `book/experiments/op-table-operation/` uses synthetic SBPL profiles to probe how op-table “buckets” (indices like 4, 5, 6) shift when we add or remove Operations and Filters, again treating bucket values as opaque equivalence classes rather than guessed Operation IDs.

This experiment, `op-table-vocab-alignment`, is intended as a bridge between those bucket-level observations and the vocabulary-mapping validation work under `book/graph/concepts/validation/`. Its objectives are:

- to define how a host-specific Operation Vocabulary Map (e.g., `out/vocab/ops.json`) can be consumed by experiments,
- to align synthetic profile data (SBPL ops, op-table buckets, operation_count) with vocabulary entries when they are available,
- to articulate what we can safely infer about bucket ↔ Operation relationships on this host, and what must remain at the “hypothesis” level.

The experiment deliberately avoids implementing the entire vocabulary-extraction pipeline itself; that work belongs to shared validation tooling. Instead, this experiment specifies the contracts and alignment logic and produces artifacts that can be reinterpreted once vocab files exist.

## 2. Scope and host baseline

This experiment targets the same Sonoma host and substrate snapshot as the existing experiments:

- **Host / OS:** macOS 14.4.1 (23E224), kernel 23.4.0, Apple Silicon; SIP enabled (from `validation/out/metadata.json`). Sonoma-era baseline consistent with `SUBSTRATE_2025-frozen`.
- **Profiles and tools reused:**
  - Synthetic SBPL variants and compiled blobs under `book/experiments/op-table-operation/sb/` and `sb/build/`.
  - Ingestion helpers and analyzers used to produce:
    - `book/experiments/op-table-operation/out/summary.json`
    - `book/experiments/op-table-operation/out/op_table_map.json`
    - `book/experiments/node-layout/out/summary.json`

Within this experiment we:

- treat these existing artifacts as read-only inputs,
- do not assume any particular Operation ID assignments beyond what a future vocabulary file will state,
- and keep all claims explicitly tied to this host / OS baseline.

## 3. Design and method (planned)

The planned method is structured in phases, corresponding to `Plan.md`:

1. **Setup and inventory**
   - Confirm the presence and shape of the existing node-layout and op-table-operation outputs.
   - Locate any vocabulary-related outputs under `book/graph/concepts/validation/out/` (for example `vocab/ops.json`, `vocab/filters.json`). If they are missing, document this as a dependency rather than a blocker.

2. **Vocabulary contract definition**
   - Define the expected JSON structure for Operation vocabulary data used by experiments, for example:
     - list of entries with `name`, `id`, and optional metadata, or
     - a map from operation name to an object containing `id`, `category`, and notes.
   - Specify how experiments should record which vocabulary version they use (OS version, build, or a hash of the vocab file).
   - Capture these expectations here so future agents implementing vocabulary extraction can target a stable interface.

3. **Alignment artifact construction**
   - Reuse existing ingestion code (or light wrappers) to:
     - enumerate synthetic profiles and their SBPL operations,
     - read `operation_count` and op-table entries for each compiled blob,
     - build a per-profile record of:
       - SBPL operation names,
       - op-table indices (buckets),
       - placeholders for Operation IDs (to be filled in once vocab exists).
   - Emit a single alignment artifact (e.g., `out/op_table_vocab_alignment.json`) that can later be augmented with concrete Operation IDs by a small post-processing step that reads the vocabulary file.

4. **Interpretation once vocab is available**
   - When a vocabulary file is present, extend the alignment process to:
     - map SBPL operation names in each profile to numeric Operation IDs,
     - note which IDs appear in which buckets (4, 5, 6, …) across all synthetic profiles,
     - highlight any stable relationships (e.g., “the ID for `mach-lookup` always appears in bucket 5 in this dataset”).
   - Keep a clear distinction between:
     - facts (directly asserted by the vocabulary file and observed op-table indices),
     - and hypotheses (patterns that might not generalize beyond these synthetic profiles).

## 4. Vocabulary contract (expected shape)

To keep alignment logic stable, this experiment assumes the vocabulary artifacts will eventually follow a simple, versioned JSON shape:

- `validation/out/vocab/ops.json`
  - `metadata`: OS/build, profile format variant, and source blobs used to derive the table (e.g., system profiles).
  - `versioning`: include product/version/build and a content hash of the vocab file so experiments can record exactly which vocabulary they consumed.
  - `entries`: list of objects with at least:
    - `name`: SBPL operation name (string).
    - `id`: numeric Operation ID (int).
    - `arg_schema` or `notes` (optional): human-readable argument description if available.
    - `provenance`: which blob(s) or tool produced the mapping.
- `validation/out/vocab/filters.json`
  - Similar structure: `name`, `id`, optional argument schema/notes, and provenance.

The current placeholder artifacts set `status: unavailable` and leave `entries` empty; once real vocab extraction runs, they should be replaced by populated tables matching the above contract, with explicit OS/build provenance.

## 4. Relationship to existing experiments

This experiment does not replace `node-layout` or `op-table-operation`; it layers on top of them:

- From `node-layout`, we borrow:
  - the structural understanding of compiled profiles (headers, op-table location, node region, literal pools),
  - and some early observations about non-uniform op-table patterns.
- From `op-table-operation`, we reuse:
  - the curated set of synthetic SBPL profiles and their compiled blobs,
  - the analytic outputs describing op-table buckets (4,5,6, …) and how they shift with Operations and Filters.

The alignment work here is meant to:

- give those experiments a clear path to connect their bucket-level findings to a canonical Operation Vocabulary Map,
- clarify which parts of the analysis must defer to shared vocabulary tooling under `book/graph/concepts/validation/`,
- and ensure that any future mapping from bucket indices to Operation IDs is explicitly versioned and grounded in canonical artifacts, in line with the substrate’s constraints.

## 5. Alignment artifact (current form)

- `book/experiments/op-table-vocab-alignment/out/op_table_vocab_alignment.json` was generated from `op-table-operation/out/summary.json` and currently records, per synthetic profile:
  - SBPL operation names,
  - observed op-table indices (`op_entries`),
  - `operation_count`,
  - placeholders for `operation_ids` and `vocab_version`.
- After creating placeholder vocabulary artifacts (`validation/out/vocab/ops.json`, `filters.json`) with status `unavailable`, the alignment file now records `vocab_present=true`, `vocab_status=unavailable`, and `vocab_version=<placeholder timestamp>`; `operation_ids` remain null until a real vocabulary map is produced.

## 6. Current status and next steps

Current status:

- The experiment has been initialized:
  - `Plan.md` describes the phases: setup, vocabulary hookup, alignment, interpretation, and turnover.
  - `Notes.md` records the creation of this experiment and its intended bridging role.
  - Existing artifacts from sibling experiments have been inventoried (`node-layout/out/summary.json`, `op-table-operation/out/summary.json`, `op_table_map.json`).
  - Placeholder vocabulary artifacts now exist under `book/graph/concepts/validation/out/vocab/` (status `unavailable`, IDs unknown) to unblock alignment consumers.
  - Ran static-format demos (`examples/extract_sbs/run-demo.sh`, `examples/sb/run-demo.sh` after fixing import path); ingestion marks system blobs as `unknown-modern` with empty op-table lengths, leaving no vocab data.
  - The alignment artifact `book/experiments/op-table-vocab-alignment/out/op_table_vocab_alignment.json` has been generated and updated to record vocab status and placeholder version; `operation_ids` remain empty pending a real vocabulary map.

Immediate next steps (for a future agent):

1. Define how to associate vocabulary artifacts with OS/build (versioning/hash) in line with the expected JSON contract, and record that mapping in `Plan.md`/`ResearchReport.md`.
2. Outline the pipeline for generating real `out/vocab/ops.json` / `filters.json` from canonical blobs (e.g., `extract_sbs` outputs), even if not implemented here.
3. Trigger or coordinate the vocabulary-mapping tasks (e.g., `op-filter-tables-from-blobs`) to populate `book/graph/concepts/validation/out/vocab/ops.json`; replace the placeholder and rerun alignment to fill `operation_ids` and record vocab version/hash.
4. Keep `Notes.md` updated with further alignment or contract-definition work; propagate any vocab dependency notes to `EXPERIMENT_FEEDBACK.md` if needed.
5. Implement or integrate a decoder that can extract operation/filter vocab from modern compiled blobs; current ingestion heuristics (op-table len=0 for system profiles) are insufficient.

As with the other experiments, `Plan.md` and `ResearchReport.md` should be kept in sync so that another agent can pick up the work with minimal re-orientation.
