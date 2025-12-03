# Vocab from Cache – Research Report (Sonoma / macOS 14.4.1)

## Purpose
Extract Operation/Filter vocab tables (name ↔ ID) from the macOS dyld shared cache (Sandbox.framework/libsandbox payloads) and align them with decoder-derived op_count/op_table data from canonical blobs, producing real `ops.json` / `filters.json` for this host.

## Baseline & scope
- Host: macOS 14.4.1 (23E224), kernel 23.4.0, arm64, SIP enabled.
- Canonical blobs for alignment:
- `book/examples/extract_sbs/build/profiles/airlock.sb.bin`
- `book/examples/extract_sbs/build/profiles/bsd.sb.bin`
- `book/examples/sb/build/sample.sb.bin`
- Current vocab artifacts (`graph/mappings/vocab/ops.json` / `filters.json`) are `status: ok` (196 ops, 93 filters) harvested from the dyld cache.

## Deliverables / expected outcomes
## Deliverables / expected outcomes
- `book/graph/mappings/vocab/ops.json` and `filters.json` for this Sonoma host, with operation and filter IDs, names, metadata, and provenance.
- Intermediate name lists in `book/experiments/vocab-from-cache/out/operation_names.json` and `out/filter_names.json`.
- Guardrail script `check_vocab.py` asserting vocab status and expected counts (196 operations, 93 filters).
- Notes in this report and `Notes.md` summarizing how vocab artifacts were derived and how they feed other experiments.

## Plan & execution log
### Completed
- **Current status**
  - Dyld shared cache located at `/System/Volumes/Preboot/Cryptexes/OS/System/Library/dyld/dyld_shared_cache_arm64e`; extracted via Swift shim using `/usr/lib/dsc_extractor.bundle` into `book/experiments/vocab-from-cache/extracted/` (Sandbox.framework + libsandbox pulled out).
  - Added `harvest_ops.py` to decode `_operation_names` → `__TEXT.__cstring`; harvested 196 ordered operation names (`out/operation_names.json`), confirming the op_count heuristic (167) was a decoder artifact.
  - Added `harvest_filters.py` to decode `_filter_info` → `__TEXT.__cstring`; harvested 93 ordered filter names (`out/filter_names.json`).
  - `book/graph/mappings/vocab/ops.json` is `status: ok` (IDs 0–195); `filters.json` now `status: ok` (IDs 0–92) from the cache harvest.
  - Regenerated `book/experiments/op-table-operation/out/*` with the vocab length override (196 ops) and refreshed `op-table-vocab-alignment` to fill `operation_ids` per profile; op_table entries now cover the full vocabulary. (Filters not yet propagated into downstream experiments.)
  - Added `check_vocab.py`, a guardrail script that asserts vocab status is `ok` and counts are ops=196, filters=93 for this host.
  - Experiment marked complete; raw cache extraction under `book/experiments/vocab-from-cache/extracted/` removed after harvesting, with trimmed copies retained in `book/graph/mappings/dyld-libs/`.
- **1) Setup and scope**
  - Recorded host baseline (OS/build, kernel, SIP) in `ResearchReport.md`.
  - Inventoried canonical blobs for alignment (system profiles plus `sample.sb.bin`).
  - Confirmed vocab artifacts and static metadata under `book/graph/mappings/vocab` and `validation/out/metadata.json`.
- **2) Cache extraction**
  - Located the dyld shared cache and extracted Sandbox-related slices (Sandbox.framework, libsandbox) into `extracted/` with provenance in `Notes.md`.
- **3) Name harvesting**
  - Implemented Python harvesters to scan extracted binaries for operation and filter name tables, using symbol-linked arrays where available.
  - Counted recovered names and compared them to decoder op_count; confirmed 196 operations and 93 filters.
- **4) ID alignment**
  - Aligned harvested names with decoder op_table/op_count and spot-checked using single-op SBPL profiles.
  - Emitted `book/graph/mappings/vocab/ops.json` and `filters.json` with `status: ok`, host/build metadata, and per-entry provenance.
  - Updated vocab artifacts with real entries and provenance.
- **5) Alignment and propagation**
  - Reran `op-table-vocab-alignment` to fill `operation_ids` and `vocab_version`, then updated alignment artifacts.
  - Added a lightweight sanity check (`check_vocab.py`) to assert vocab status and counts.
  - Noted key bucket↔Operation ID relationships (e.g., mach-lookup in buckets {5,6}) in this ResearchReport and in the op-table experiments.

### Planned
- 1. Extract Sandbox-related binaries from the dyld shared cache.
  2. Harvest operation/filter name tables from the extracted binaries.
  3. Align harvested names with decoder op_count/op_table from canonical blobs; emit real vocab artifacts.
  4. Rerun op-table alignment to fill operation IDs and record bucket↔ID relationships.
- **1) Setup and scope**
  - None for this section.
  - `Plan.md`, `Notes.md`, `ResearchReport.md` in this directory.
  - A script to extract Sandbox-related binaries from the dyld shared cache.
- **2) Cache extraction**
  - None for this section.
  - Extracted binaries and a short note in `Notes.md` describing commands used and any issues.
- **3) Name harvesting**
  - None for this section.
  - `harvest.py` (or similar) that emits candidate name lists with offsets/order.
  - Intermediate JSON with recovered names and inferred ordering.
- **5) Alignment and propagation**
  - Refresh alignment and bucket snapshots only if vocab artifacts are regenerated for a new host/build.
  - Updated alignment file with IDs and vocab hash/version.
  - Notes/report entries summarizing bucket-to-ID findings (scoped to this host).

## Evidence & artifacts
- Extracted Sandbox.framework/libsandbox slices from the dyld shared cache under `book/experiments/vocab-from-cache/extracted/` (transient) and trimmed copies in `book/graph/mappings/dyld-libs/`.
- `out/operation_names.json` and `out/filter_names.json` harvested from the extracted binaries.
- Published vocab artifacts `book/graph/mappings/vocab/ops.json` and `filters.json` with host/build metadata.
- `check_vocab.py` and any downstream experiment outputs regenerated using the new vocab (e.g., refreshed `op-table-operation` and `op-table-vocab-alignment` artifacts).

## Blockers / risks
- Vocab extraction is tied to this host’s dyld cache layout; changes in future OS versions may require revisiting the harvesters and their assumptions.
- Vocab artifacts are a shared dependency; accidental edits or regeneration on a different host/build could silently desynchronize them from the rest of the mapping layer.

## Next steps
- Treat the current vocab artifacts as the canonical Operation/Filter vocabularies for this host and only regenerate them deliberately (with updated metadata) when the underlying cache or decoding logic changes.
- Keep downstream experiments (especially `op-table-operation`, `op-table-vocab-alignment`, and `field2-filters`) aligned with the vocab version recorded in `ops.json`/`filters.json`.
