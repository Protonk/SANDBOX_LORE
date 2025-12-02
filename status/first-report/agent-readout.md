# Agent readout — repo status (Sonoma host, macOS 14.4.1 / 23E224)

This is a fresh read-in for an agent with no prior context. Vocabulary and lifecycle align to the substrate (Orientation/Concepts/State). Host baseline for current artifacts: macOS 14.4.1 (23E224), kernel 23.4.0, Apple Silicon, SIP enabled.

## Experiments (book/experiments)
- **anchor-filter-map** — Map published at `book/graph/mappings/anchors/anchor_filter_map.json` (with host metadata). High-confidence anchors: `/tmp/foo`, `/etc/hosts` → path (id 0); `/var/log` → ipc-posix-name=4; `idVendor` → local-name=6; `preferences/logging` → global-name=5. Ambiguous anchors remain noted. Guardrail lives in `tests/test_mappings_guardrail.py`.
- **system-profile-digest** — Curated digests for `airlock`, `bsd`, `sample` at `book/graph/mappings/system_profiles/digests.json` with host/build metadata. Guardrailed via tests.
- **tag-layout-decode** — Published literal/regex tag layouts at `book/graph/mappings/tag_layouts/tag_layouts.json` (record_size=12, edges in fields[0..1], payload in field[2] for tags 0,1,3,5,7,8,17,26,27,166). Guardrail added. Used by decoder.
- **vocab-from-cache** — Operation/filter vocab harvested from dyld cache; `book/graph/mappings/vocab/ops.json` (196) and `filters.json` (93) are treated as `status: ok` in the validation index, with guardrail `check_vocab.py`. Trimmed cache copies parked under `book/graph/mappings/dyld-libs/`.
- **op-table-vocab-alignment** — Aligns op-table buckets from synthetic profiles to vocab IDs; artifact `book/graph/mappings/op_table/op_table_vocab_alignment.json` with `vocab_status: ok`. Bucket summary: file-read*/write*/network-outbound IDs land in buckets {3,4}; mach-lookup (ID 96) in {5,6}, with bucket 6 only in mach+filtered-read mixes.
- **op-table-operation** — Bucket-level behavior catalogued: unfiltered read/write/network → bucket 4; mach-only and filtered read-only → bucket 5; mach + filtered read → `[6,…,5]` pattern. Entry signatures captured in `out/op_table_signatures.json`. Needs runtime confirmation and finer per-slot mapping in `[6,…,5]`.
- **node-layout** — Structural decode baseline: modern profiles = 16-byte preamble + op-table + node region + literal pool. Front parses well as 12-byte nodes; tail remains irregular. `field2` appears as a branch/filter key (values 0/3/4/5/6) independent of literal content. Open: tag semantics, tail layout, filter-ID binding. Tooling lives in `analyze.py`, summaries in `out/summary.json`.
- **field2-filters** — `out/field2_inventory.json` aggregates system profiles + single-filter probes. Low `field2` IDs align with path/name filters; high IDs in `airlock` remain unknown. Synthetic probes still dominated by generic path/name scaffolding; filter-specific mapping unresolved. Next step: richer tag-aware decode + anchor-backed probes.
- **probe-op-structure** — Anchor-aware probes compiled; anchor scan now emits literal offsets and node hits, but hits still carry generic `field2` values. Segment-aware slicing added. Blocked on tag-aware node decode to expose literal/regex operands and firm `field2` ↔ filter mapping. Outputs under `out/anchor_hits.json` and tag inventories.
- **runtime-checks** — Harness now prefers `book/api/SBPL-wrapper/wrapper` (SBPL/blob). Bucket profiles and system blobs are wired through this path; on this host `sandbox_init`/`sandbox_apply` failures dominate (EPERM for platform blobs in blob mode), so `out/runtime_results.json` is currently apply-failure heavy rather than clean allow/deny evidence. Matrix/expected shapes live in `out/expected_matrix.json`.
- **sbpl-graph-runtime** — SBPL→graph→runtime triples incomplete. `allow_all` behaves as expected; strict `(deny default)` shapes currently apply but runtime results do not match expected denies (probes succeed where denies were expected). Profiles and harness need adjustment before treating these triples as reliable; manifest not yet built.
- **entitlement-diff** — Sample binaries signed with/without `com.apple.security.network.server`; entitlements extracted to `out/*.entitlements.plist`. Blocker: deriving App Sandbox profiles per entitlement variant and running probes via wrapper; runtime delta not yet measured.
- **symbol-search** — Ghidra headless scans of BootKernelExtensions.kc still hunting the PolicyGraph dispatcher. No AppleMatch imports or MACF hook chain resolved yet; candidate pointer tables found but unreferenced. Needs ARM64-aware ADRP/ADD sweeps and mac_policy_ops pivot.

## Concept inventory & validation state (book/graph/concepts)
- **Concept inventory** clusters (static-format, semantic graph/evaluation, vocabulary/mapping, lifecycle/extension) are documented in `CONCEPT_INVENTORY.md` and cluster-tagged in `validation/Concept_map.md`.
- **Validation harness** (`validation/README.md`, `tasks.py`):
  - Static-format: active. Ingestion outputs at `validation/out/static/{sample.sb.json,system_profiles.json,mappings.json}`; profile format variant recorded as modern-heuristic.
  - Vocabulary: active. `validation/out/vocab/{ops.json,filters.json,operation_names.json,filter_names.json}` mirrored from vocab-from-cache; treated as `status: ok` in the validation index.
  - Semantic graph: still not providing trustworthy evidence. Legacy sandbox-exec logs exist (`metafilter.jsonl`, `network.jsonl`, `mach_services.jsonl`, `sbpl_params.jsonl`) but are flagged brittle, and wrapper-based runs in `validation/out/semantic/runtime_results.json` show both successes and mismatches; the cluster is kept provisional.
  - Lifecycle/extension: partial. `entitlements.json` captured; `extensions_dynamic.md` notes expected EPERM; other lifecycle probes not rerun.
  - Index at `validation/out/index.json` summarizes cluster status and pointers; baseline metadata in `validation/out/metadata.json`.

## Tooling surface (book/api)
- **Decoder (`book.api.decoder`)** — Heuristic modern-profile decoder with tag-layout integration and section offsets; emits op-table, nodes (tag-aware when layouts exist), literal pool, validation counters. CLI: `python -m book.api.decoder dump <blob>`. Downstream experiments depend on this output.
- **SBPL wrapper (`book/api/SBPL-wrapper/wrapper`)** — Supports `--sbpl` and `--blob` (README lags). Used by runtime-checks; blob apply works for `bsd` on this host, `airlock` denied EPERM. Build: `clang -Wall -Wextra -o wrapper wrapper.c -lsandbox`.
- **Ghidra connector (`book/api/ghidra`)** — Task registry and headless runner wrapping `dumps/ghidra` scripts. Keeps HOME/TMPDIR under `dumps/ghidra` to avoid sandbox prompts; scripts live in `book/api/ghidra/scripts/`.
- **File probe** — `book/api/file_probe/file_probe` binary used by runtime harnesses for simple filesystem probes.

## Ready-to-use artifacts (graph/mappings)
- Vocab tables (`vocab/ops.json`, `vocab/filters.json`) are treated as `status: ok` in the validation index.
- Op-table buckets/signatures and vocab alignment (`op_table/*.json`).
- Tag layouts (`tag_layouts/tag_layouts.json`), anchor→filter map (`anchors/anchor_filter_map.json`).
- System profile digests (`system_profiles/digests.json`).
- Guardrails in `tests/test_mappings_guardrail.py` and `tests/test_runtime_matrix_shape.py` cover presence/shape.

## Gaps and suggested next actions
- Semantic validation is the main hole: platform blobs fail apply on this host and SBPL microprofiles have runtime/expectation mismatches, so neither runtime-checks nor sbpl-graph-runtime yet provide solid semantic evidence. Options: run on a permissive host, adjust profiles/harness, or extend wrapper to handle apply quirks.
- `field2` and literal/regex operand decoding remain partially unknown; invest in tag-aware node decode and anchor-backed probes (probe-op-structure + field2-filters).
- Entitlement-driven profile derivation/probes: build App Sandbox SBPL per entitlement variant and rerun runtime tests via wrapper.
- Kernel dispatcher hunt: pivot via mac_policy_ops and ARM64 ADRP/ADD sweeps; intersect with any AppleMatch callers when found.
