# Runtime probes

Runtime probe outputs that are stable enough to reuse live here. These are versioned to the Sonoma baseline (23E224) and come from the same harness used by `book/graph/concepts/validation/out/semantic/runtime_results.json`.

Current artifacts:
- `expectations.json` — manifest keyed by `profile_id` with host/build/SIP metadata, blob path + SHA256, status (`ok`/`partial`/`blocked`), probe count, and the trace file path.
- `traces/*.jsonl` — normalized per-profile probe rows (`profile_id`, `probe_name`, operation name/id, inputs, expected vs actual, match/status, command, exit code) with vocab IDs attached. Sources point back to the validation log for provenance.

Role in the substrate:
- Adds the enforcement layer to the static mappings: which Operations (by vocab ID) and inputs were allowed/denied under specific compiled profiles on this host.
- Lets consumers mechanically join runtime outcomes to static structure (op-table vocab, digests, tag layouts) without re-parsing validation logs.
- Status fields carry through harness limits (e.g., partial bucket5 traces, apply gates) so downstream users do not silently upgrade brittle evidence.

Regeneration:
- Rerun `book/graph/concepts/validation/out/semantic/runtime_results.json` (via `runtime-checks`) and normalize into this folder using a small loader (see `expectations.json` for the expected shape). Keep host/build metadata aligned with `validation/out/metadata.json`.
