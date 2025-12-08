# Post-remediation promotion proposal

World: `sonoma-14.4.1-23E224-arm64-dyld-2c0602c5`. Bedrock here means “safe to treat as fixed inputs for this world, with explicit status/demotion paths if evidence drifts.”

## Operation vocabulary (196 ops / 93 filters)
**Claim / representation / use**
- Canonical Operation/Filter vocab tables live in `book/graph/mappings/vocab/ops.json` and `filters.json` (`status: ok`, world-pinned). IDs are ordered as harvested from `libsandbox` and are the only allowed op/filter names for this world; this is a freeze to the host’s own published tables, not to the current profile corpus.
- Downstream: op-table alignment (`book/graph/mappings/op_table/op_table_vocab_alignment.json`), system-profile digests (`system_profiles/digests.json` op_table_len/hash), ops coverage (`vocab/ops_coverage.json` marks runtime_evidence vs structural-only), CARTON manifest entries, and API helpers (`book/api/carton/carton_query.py`) assume these IDs are stable.

**Evidence**
- **Validation**: `validation_status.json` records `vocab:sonoma-14.4.1` as `ok-unchanged` with counts 196/93, input `book/graph/mappings/dyld-libs/usr/lib/libsandbox.1.dylib`, outputs `ops.json`/`filters.json`. Guardrails `book/tests/test_vocab_harvest.py` assert harvested name lists (`book/experiments/vocab-from-cache/out/*`) exactly match `ops.json`/`filters.json`, including ordering and sequential IDs. `book/tests/test_dyld_libs_manifest.py` covers the trimmed dyld slices. This means “only allowed names” is keyed to the host’s dyld-derived tables; if Apple ships additional ops/filters, the harvest/manifest checks will surface and force a status change.
- **Cross-check**: Op IDs appear consistently in op-table alignment (`op_table_vocab_alignment.json` carries `vocab_versions` with `status: ok`) and in system-profile digests (op_table_len/op_table_hash fields) derived from independent compiled blobs. Ops coverage flags runtime-backed ops (`file-read*`, `file-write*`, `mach-lookup`) in `ops_coverage.json` and CARTON coverage (`carton/operation_coverage.json`), confirming IDs line up with runtime probes.
- **Independence**: Vocab harvest comes directly from dyld cache strings (`vocab-from-cache`), independent of the decoder/ingestion path used by op-table/system-profile work. Alignment and digests consume SBPL→blob→decoder pipelines; shared failure would require both the dyld slice and decoder to fail in the same way. Manifest + harvest guardrails catch drift in the slice; alignment/digest guardrails catch decoder/plumbing errors.

**Boundaries / failure modes**
- Scope is this world only; cross-version reuse is unsupported. If dyld slices or harvested name order drift, `test_vocab_harvest`/manifest checks will fail and `vocab` validation will demote. If op-table or digest consumers stop agreeing on ID counts/hashes, op-table and system-profile guardrails will trip. Runtime evidence exists for only a subset of ops; `ops_coverage.json` marks the rest as structural-only. The freeze does not claim “no other ops exist in the universe,” only “for this world the exported vocab tables enumerate all ops/filters the compiler knows about.”

## Modern compiled profile format and tag layouts
**Claim / representation / use**
- Modern profiles on this host follow the `modern-heuristic` layout (16-byte preamble, op-table, node region, literal/regex pool). Literal/regex-bearing tags use the per-tag layouts in `book/graph/mappings/tag_layouts/tag_layouts.json` (`status: ok`, world-pinned, canonical_profile status imported). Covered tags: `[0,1,3,5,7,8,17,26,27,166]`. “Bedrock” applies to this covered subset because both decoder-side inference and compiler-side emission agree on field placement and we have guardrails/demotion wired to canonical profiles.
- Downstream: decoder (`book/api/decoder`) and inspection tools prefer these layouts to interpret payload fields; static checks (`system_profiles/static_checks.json`) record the `tag_layout_hash`; system-profile digests and tag-layout metadata propagate canonical status for demotion; anchor/filter mapping and runtime signature decoding depend on these layouts.

**Evidence**
- **Validation**: Decoder health is exercised in `book/tests/test_decoder_headers.py` and `test_decoder_validation.py` (sections, validation fields). Tag-layout mapping presence/shape is guarded in `book/tests/test_mappings_guardrail.py`; `book/tests/test_tag_layout_hash.py` enforces that the contract hash ignores metadata-only edits and flips on tag changes. `tag_layouts.json` metadata mirrors canonical profile status via `tag_layouts/annotate_metadata.py` so demotion propagates automatically.
- **Cross-check**: Tag layouts are inferred from decoded canonical profiles in `book/experiments/tag-layout-decode/out/` and promoted to `tag_layouts.json`; `book/experiments/libsandbox-encoder/out/tag_layout_overrides.json` confirms payload field placement (e.g., tag10 filter_id/payload) at the byte level from the compiler side. Static checks (`system_profiles/static_checks.json`) carry `tag_layout_hash`, and `test_canonical_drift_scenario.py` shows demotion propagation into tag layouts and CARTON coverage if canonical profiles drift.
- **Independence**: Decoder-side inference (tag-layout-decode using canonical blobs) is independent of compiler-side emission (libsandbox-encoder matrices and raw node dumps). Both routes share SBPL→libsandbox compilation but differ in parsing vs emission, reducing common-mode risk. Validation tests exercise decoder output separately from mapping generation.

**Boundaries / failure modes**
- Coverage is limited to the literal/regex-bearing tags listed above; unknown tags still fall back to stride-12 decoding. Format is still marked “heuristic” in `validation/out/metadata.json`; tail layouts beyond literal-bearing tags remain partially characterized. A decoder bug could affect both tag-layout-decode and static checks, but compiler-side evidence (libsandbox-encoder) would disagree. Canonical-profile drift will demote tag-layout status automatically; metadata/tags hash separation prevents silent metadata churn. If new tags show up, the current mapping is explicitly incomplete rather than silently wrong.

## Canonical system profiles (`sys:airlock`, `sys:bsd`, `sys:sample`)
**Claim / representation / use**
- `book/graph/mappings/system_profiles/digests.json` publishes canonical structural digests for the three curated profiles with contracts (blob sha/size, op_table hash/len, tag_counts, tag_layout_hash, world pointer) and `status: ok`. Canonical set is fixed and tied to world_id; the bedrock claim is that these are the exact blobs the kernel would consume on this host, frozen by hash and contract.
- Downstream: tag-layout metadata imports canonical status; CARTON coverage and indices (`carton/operation_coverage.json`, `operation_index.json`, `profile_layer_index.json`) mirror canonical status; runtime expectations (`runtime/golden_expectations.json`) and attestations (`system_profiles/attestations/*.jsonl`) link SHAs to runtime signatures where applicable.

**Evidence**
- **Validation**: `validation_status.json` records `experiment:system-profile-digest` as `ok-unchanged`; inputs are `book/experiments/system-profile-digest/out/digests.json`. Generator `generate_digests_from_ir.py` enforces contract fields, uses `generate_static_checks.py`, and requires validation `ok`. Guardrails `book/tests/test_mappings_guardrail.py` and `test_system_profiles_mapping.py` assert presence, world pointer, contract fields, and `status: ok`.
- **Cross-check**: Static checks (`system_profiles/static_checks.json`) confirm header op_count, section sizes, tag counts, tag_layout_hash and blob SHA/size. Attestations (`system_profiles/attestations/*.jsonl`) enumerate literals/anchors, vocab versions, and runtime links. CARTON manifest includes `system_profiles/digests.json`, and demotion propagation is exercised in `book/tests/test_canonical_drift_scenario.py` (drift → brittle in digests → tag layouts → coverage/indices).
- **Independence**: Digests are derived from compiled blobs via decoder; static checks recompute sizes/hashes independently of the digest generator; attestations re-walk blobs for literals/anchors; CARTON hash verification adds an external check. Runtime probes cannot apply platform profiles on this host (apply gate) but SHAs are wired into `runtime/golden_expectations.json` to keep runtime linkage explicit when possible.

**Boundaries / failure modes**
- Contracts are strict snapshots of the current blobs; drift in any contract field demotes status to `brittle` with recorded `drift_fields` and propagates downstream (tag layouts, coverage, CARTON indices). Apply gates remain an environmental limitation, not evidence against the blobs; the kernel still consumes these compiled profiles, and we treat the hashed, cross-checked structure as the ground truth for that kernel input. Decoder/shared ingestion bugs could affect digests and static checks together; attestations and CARTON hash checks provide an independent pass over the same blobs.

## Recommendation
All three concepts meet the bedrock bar for this world:
- Validation jobs are `ok`, guardrails exist, and demotion paths are explicit.
- Independent routes agree (dyld harvest vs op-table/system profiles for vocab; decoder vs compiler-side for tag layouts; digests vs static checks vs attestations for canonical profiles).
- Boundaries are documented (runtime coverage limits, tag coverage scope, apply gates).

Treat them as bedrock, with the demotion story above as the falsification path if future evidence drifts.
