# Anchor ↔ Filter ID Mapping – Notes

Use this file for dated, concise notes on progress, commands, and intermediate findings.

## 2025-12-10

- Experiment scaffolded (plan/report/notes). Goal: convert anchor hits into a filter-ID map, landing at `book/graph/mappings/anchors/anchor_filter_map.json`. No data pass yet.

## 2025-12-11

- Baseline data pass: loaded `probe-op-structure/out/anchor_hits.json` and harvested anchors with field2 hints; wrote initial candidates to `out/anchor_filter_candidates.json` (anchor → {field2_names, field2_values, sources}). Field2 inventory not yet merged; next step is disambiguation and mapping to filter IDs.
- Produced first `anchor_filter_map.json` in `book/graph/mappings/anchors/` (now with host metadata). Mapped: `/tmp/foo` and `/etc/hosts` pinned to `path` (id 0) for file probes, `/var/log` → ipc-posix-name=4, `idVendor` → local-name=6, `preferences/logging` → global-name=5; others remain `status: ambiguous` with candidates noted. Guardrail `tests/test_mappings_guardrail.py` ensures map presence and at least one mapped entry.
