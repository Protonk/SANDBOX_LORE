# Op-table vs Operation Mapping – Notes

## 2025-11-27 1

- Initialized a new experiment under `book/experiments/op-table-operation` to map SBPL operation names to op-table entry indices in compiled profiles.
- Drafted `Plan.md` with a scope focused on core ops (`file-read*`, `file-write*`, `mach-lookup` with `com.apple.cfprefsd.agent`, `network-outbound`, plus a baseline/no-op profile), single-op and paired-op profiles, reuse of the existing analyzer, and a correlation artifact `out/op_table_map.json`.
- Set expectations for artifacts: `sb/*.sb` variants and `sb/build/*.sb.bin` blobs, `out/summary.json` via analyzer/wrapper, and correlation JSON for op-table mapping. Cross-checks with existing semantic probes are noted as an optional stretch.
- Next steps: create the `sb/` variants, wire the analyzer/wrapper, generate `summary.json`, and build the initial op-table correlation.

## 2025-11-29 2

- Created this note block to log execution/troubleshooting while standing up the experiment.
- Added `sb/` variants covering the planned ops:
  - `v0_empty` (deny default only), `v1_read`, `v2_write`, `v3_mach` (cfprefsd), `v4_network`.
  - Paired mixes differing by one op: `v5_read_write`, `v6_read_mach`, `v7_read_network`, `v8_write_mach`, `v9_write_network`, `v10_mach_network`.
- No analyzer wiring yet; next step is to stand up a wrapper (reuse node-layout analyzer or a slim copy) and generate summaries.
- Implemented `analyze.py` in this experiment to compile all `sb/*.sb`, emit `out/summary.json`, and a simple `out/op_table_map.json` that records ops, op_entries, and unique entry values per profile plus single-op hints. Added a literal/tag summary for quick inspection.
- First run exposed a parsing bug: `parse_ops` grabbed the entire `(allow …)` clause (including filter) for `mach-lookup`; fixed regex to capture only the operation symbol and reran.
- Current outputs (post-fix):
  - Single-op profiles: read/write/network share uniform op entries `[4,…]` (op_count=5); mach-only profiles use `[5,…]` (op_count=6).
  - Paired combos: read+write/read+network/write+network remain `[4,…]`; any combo including mach remains `[5,…]`.
  - The baseline `v0_empty` also shows `[4,…]` with op_count=5.
  - `op_table_map.json` now records single-op entries: {read: [4], write: [4], network: [4], mach: [5]} and per-profile unique entries (either {4} or {5}). No non-uniform op-table entries observed in this batch.
- Next steps: craft asymmetric mixes that reproduce the `[6,…,5]` pattern from the node-layout experiment (e.g., include subpath literals) or add analyzer logic to correlate op_table slots across differing op_count shapes; update Plan/Report accordingly.

## 2025-11-29 3

- New goal: reintroduce filters/literals in this op-table experiment to see if the `[6,…,5]` pattern resurfaces and to try to pin the lone `5` to a specific op.
