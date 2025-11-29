# SBPL ↔ Graph ↔ Runtime – Notes

Use this file for dated, concise notes on commands, hurdles, and intermediate results.

## 2026-01-XX

- Authored minimal profiles: `allow_all.sb`, `deny_all.sb`, `deny_except_tmp.sb`, `metafilter_any.sb` (param_path.sb exists but fails to compile without param injection).
- Compiled via `book/examples/sbsnarf/sbsnarf.py` (absolute paths) → binaries in `out/*.sb.bin`.
- Decoded headers/sections into `out/ingested.json` using `profile_ingestion.py` (modern-heuristic variant).
- Runtime probes not run yet; existing harnesses blocked by SIP/EPERM on this host. Need SIP-relaxed environment or alternative runner for the “runtime” leg of the triples.
