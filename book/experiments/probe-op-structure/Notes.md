# Probe Op Structure – Notes

Use this file for dated, concise notes on probe designs, compile logs, and findings.

## 2025-12-03

- Experiment initialized. Vocab artifacts available (ops: 196, filters: 93). Pending: define probe matrix that mixes multiple filters/ops and deeper metafilters to tease out filter-specific `field2` values beyond generic path/name nodes.
- Added initial probe matrix and SBPL variants:
  - Single-op file variants: `v0_file_require_all`, `v1_file_require_any`, `v2_file_three_filters_any`.
  - Single-op mach/network/iokit: `v3_mach_global_local`, `v4_network_socket_require_all`, `v5_iokit_class_property`.
  - Mixed variants: `v6_file_mach_combo`, `v7_file_network_combo`, `v8_all_combo`.
- Compiled via `libsandbox`; decoded with vocab padding. Early observations from `out/summary.json`:
  - Field2 remains dominated by low IDs: `global-name` (5), `local-name` (6), `ipc-posix-name` (4), `file-mode` (3), `remote` (8). Even filter-diverse profiles surface these generic IDs.
  - Network profile (`v4`) shows `remote` (8) from graph walk; file/network combo (`v7`) shows `remote` for both ops.
  - Mach/global/local variants show {5,6}; file-only require-all/any variants show {3,4} or {5,6} depending on decoder op_count.
  - Decoder heuristic failed on `v8_all_combo` (node_count 0, all ops bucket 0) likely due to literal-start detection; needs better slicing if we revisit.
- Revised plan (do not implement yet): shift to anchor-based traversal and improved slicing:
  - Add segment-aware slicing fallback to avoid node_count=0 on complex profiles.
  - Use literal anchors (unique paths, mach names, iokit classes) to locate filter-specific nodes and read their `field2`.
  - Design profiles with disjoint anchors per filter family and multi-op separation to reduce path/name masking.
  - Cross-check with system profiles and add guardrails once mappings stabilize.
- Ran `analyze_profiles.py` to gather field2 histograms and literal samples for probes and system profiles (`out/analysis.json`):
  - Probes still dominated by low/generic IDs: file probes heavy on `ipc-posix-name`/`file-mode`; mach/iokit variants show {5,6}; network shows {8,7} plus occasional `xattr`/unknown 2560.
  - System profiles reaffirm higher-ID filters (`bsd`: 27=`preference-domain`, 26=`right-name`, etc.; `sample`: low path/socket IDs; `airlock`: high unknowns 166/165/10752).
  - Literal samples confirm anchors present (e.g., `/tmp/foo`, `/etc/hosts`, mach service, iokit class), but decoder traversal still does not reach filter-specific nodes; masking persists.
- Added `anchor_map.json` (anchor strings per profile) and `anchor_scan.py` to search for anchors → node indices → `field2`. Current results (`out/anchor_hits.json`):
  - Anchors are found in literal strings (e.g., `/tmp/foo`, `/etc/hosts`, mach name, iokit class), but `node_indices` remain empty across probes/system profiles—decoder node fields aren’t directly pointing to anchor offsets with current slicing.
  - Confirms we need better node/literal association (segment-aware slicing or richer node decoding) to bridge anchors to nodes and `field2`.
- Implemented a minimal Mach-O segment parser in `profile_ingestion.py` to improve slicing; reran `analyze_profiles.py` with the fallback. `v8_all_combo` now slices nodes (nodes_len=424) but anchor_scan still fails to link anchors to nodes (empty `node_indices`), indicating node→literal references are not captured by the current decoder fields.
- Brute inspection of `v1_file_require_any`:
  - Anchors reside in the literal pool as prefixed strings (`Ftmp/foo`, `Hetc/hosts`) at offsets ~461/477.
  - Node fields (stride-12 heuristic) only contain small values {0,1,2,3,5,6}; no values near literal offsets, so anchors do not show up in decoded node fields.
  - Conclusion: the current heuristic node parsing exposes filter IDs but not literal offsets; node↔literal association will require a richer decode of modern node records beyond the simple 12-byte/field view.
- Updated `anchor_scan.py` to use raw section slicing and search node bytes for anchor offsets (relative/absolute) with strides 12/16. Anchors in literal pools are located (e.g., `/tmp/foo` at offset ~43 within pool), but no node bytes contain these offsets; `node_indices` remain empty. Fields still only carry small filter-ID-like values, confirming we need a deeper node decoder to expose literal references.
- Planning next steps (anchor-based slicing/traversal):
  - Implement segment-aware slicing fallback (Mach-O offsets for node/literal boundaries) to avoid node_count=0 cases like `v8_all_combo`; record when fallback is used.
  - Enforce anchor uniqueness per filter family; generate anchor maps per profile.
  - Traverse by anchor: find nodes referencing anchors and record `field2`/tags/op-table context, using op-entry walks only as secondary context.
  - Cross-check anchor hits against system profiles; note mismatches.
  - Persist all intermediate JSON (segment offsets, slices, anchor hits, field2 findings) and dated notes; keep mappings versioned to host/build.
  - Once mappings emerge, produce a small artifact (filter ID/name ↔ observed field2 with provenance) and a guardrail checker that asserts expected `field2` for given anchors.
