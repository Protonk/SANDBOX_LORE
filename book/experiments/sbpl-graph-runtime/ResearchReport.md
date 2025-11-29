# SBPL ↔ Graph ↔ Runtime – Research Report

## Purpose

Demonstrate round-trip alignment between SBPL source, compiled graph structure, and runtime allow/deny outcomes on a small set of canonical profiles. Provide concrete triples that witness semantic concepts and tie into static/vocab views.

## Baseline

- Host: TDB (record OS/build/SIP when runs are performed).
- Tooling: reuse `profile_ingestion.py` for decoding; use a lightweight probe harness (sandbox-exec or local runner) for runtime checks.
- Profiles: allow-all/deny-all, deny-except, filtered allow, metafilter, parameterized path.

## Status

- Profiles authored: allow_all, deny_all, deny_except_tmp, metafilter_any (param_path pending param injection).
- Compiled to binaries with `sbsnarf.py` (absolute paths) and decoded via `profile_ingestion.py`; see `out/ingested.json` for header/section summaries (modern-heuristic).
- Runtime probes not yet captured: both sandbox-exec and sandbox_init-based runners fail with EPERM on this host under SIP. Triples are currently “SBPL + graph” only; runtime leg deferred until a permissive environment is available.
