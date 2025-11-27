# Op-table vs Operation Mapping – Research Report (skeleton)

This report will summarize an experiment to map SBPL operation names to op-table entry indices and observed graph entrypoints in compiled sandbox profiles on a Sonoma host. It will draw on synthetic SBPL profiles, compiled blobs, analyzer outputs, and any semantic probe cross-checks.

##  Motivation and objectives

##  Setup and tools (SBPL variants, analyzer/wrapper, correlation script)

##  Profiles and methods

##  Findings (op_table mappings, node/tag deltas)

##  Open questions and next steps

## Current progress snapshot

- SBPL variants exist for baseline, single-op (read/write/mach-lookup/network), and paired-op mixes; compiled blobs generated via libsandbox.
- Analyzer (`analyze.py`) emits `out/summary.json` and `out/op_table_map.json`. Single-op entries suggest:
  - `file-read*`, `file-write*`, `network-outbound` → uniform op-table value 4 (op_count=5).
  - `mach-lookup` → uniform op-table value 5 (op_count=6).
- Paired combinations remain uniform ({4} or {5}); no non-uniform op-table entries observed yet in this experiment.
- Next actions: craft asymmetric profiles (e.g., add subpath/literal filters) to reproduce the `[6,…,5]` pattern seen in node-layout work and correlate op-table slots across profiles; consider extending the analyzer to perform automatic slot→op inference once a vocab map is available.
