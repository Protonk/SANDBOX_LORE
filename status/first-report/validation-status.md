# Validation status — concept coverage (macOS 14.4.1 / 23E224)

This tracks progress toward validating the concept inventory against real artifacts. Cluster names follow `CONCEPT_INVENTORY.md` and `validation/Concept_map.md`. Baseline metadata sits in `book/graph/concepts/validation/out/metadata.json` (modern-heuristic format, SIP enabled, arm64).

## Static-format cluster
- **Status:** Largely validated on this host.
- **Evidence:** `validation/out/static/{sample.sb.json,system_profiles.json}` from shared ingestion; `validation/out/static/mappings.json` routes to stable mappings (op_table, tag_layouts, anchors, system_profile digests).
- **Guardrails:** `tests/test_mappings_guardrail.py` asserts presence/shape of digests, tag layouts, anchor map; decoder is wired to tag layouts.
- **Gaps:** Tail layout and per-tag semantics remain partially opaque in `node-layout`; `field2`→filter binding still unresolved (see semantic/vocab notes).

## Vocabulary/mapping cluster
- **Status:** Operation and filter vocab harvested and aligned; runtime usage missing.
- **Evidence:** `validation/out/vocab/{ops.json,filters.json,operation_names.json,filter_names.json}` (status `ok`, counts 196/93) from `vocab-from-cache`. `op_table/op_table_vocab_alignment.json` ties synthetic profiles to operation IDs. Anchor→filter map present (`anchors/anchor_filter_map.json`).
- **Guardrails:** `check_vocab.py` and mapping guardrails; vocab mirrored in `graph/mappings/vocab/`.
- **Gaps:** Runtime usage table (`validation/out/vocab/runtime_usage.json`) is `blocked` because sandbox_init failed; filter-ID linkage to `field2` and bucket shifts is still hypothesis-only.

## Semantic graph/evaluation cluster
- **Status:** Blocked on runtime harness; only brittle sandbox-exec logs exist.
- **Evidence:** Legacy runs (`metafilter.jsonl`, `sbpl_params.jsonl`, `network.jsonl`, `mach_services.jsonl`) flagged brittle; `validation/out/semantic/runtime_results.json` records EPERM from sandbox_init despite wrapper attempts. Experiments `runtime-checks` and `sbpl-graph-runtime` have partial harnesses but lack stable allow/deny evidence.
- **Gaps:** No reliable SBPL→graph→runtime triples; cannot yet tie PolicyGraph paths to observed decisions. Need a permissive host or adjusted profiles/harness to gather semantic probes.

## Lifecycle/extension cluster
- **Status:** Partial.
- **Evidence:** `validation/out/lifecycle/entitlements.json` (entitlements-evolution) and `extensions_dynamic.md` noting expected EPERM. Other lifecycle tasks (containers, platform-policy, sandbox-apply) not rerun with the current harness.
- **Gaps:** No validated evidence for Policy Stack Evaluation Order, extensions in practice, or container path resolution on this host. `entitlement-diff` experiment still lacks App Sandbox profile derivation and runtime probes.

## Immediate steps to advance validation
- Recover semantic evidence: run `runtime-checks`/`sbpl-graph-runtime` via `book/api/SBPL-wrapper/wrapper` on a permissive host or with profiles that avoid sandbox_init EPERM; capture JSONL probes per `validation/tasks.py`.
- Finish `field2`/tag-aware decode: extend node decoder to expose literal/regex operands, rerun `probe-op-structure` to bind anchors→nodes→filter IDs, and refresh `field2_inventory.json`.
- Propagate filter IDs into op-table alignment: correlate filtered-read bucket shifts with `filters.json` entries once `field2` is mapped.
- Resume lifecycle probes: derive App Sandbox SBPL per entitlement variant (entitlement-diff), rerun extensions/containers/platform-policy tasks, and log under `validation/out/lifecycle/`.
