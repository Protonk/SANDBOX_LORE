# Field2 Atlas — Research Report — **Status: partial**

## Purpose
Follow specific field2 IDs (0 `path`, 5 `global-name`, 7 `local`) end-to-end across tag layouts, anchors, canonical system profiles, and a tiny runtime harness. Field2 is the primary key: we start from a field2 ID and ask where it shows up and what happens at runtime when we poke it.

## Position in the book
This is the canonical example of a field2-first view. It is intentionally narrow (0/5/7 + one static-only neighbor) and wires directly into existing mappings and runtime traces rather than trying to cover all field2 values.

## Setup
- World: `world_id sonoma-14.4.1-23E224-arm64-dyld-2c0602c5`.
- Seed set: fixed in `field2_seeds.json` (0/5/7 with anchors + profile witnesses).
- Inputs: `book/graph/mappings/vocab/{ops.json,filters.json}`, `book/graph/mappings/tag_layouts/tag_layouts.json`, `book/graph/mappings/anchors/anchor_filter_map.json`, `book/graph/mappings/system_profiles/{digests.json,static_checks.json}`, `book/experiments/field2-filters/out/field2_inventory.json`, runtime signatures/traces under `book/graph/mappings/runtime/` (notably `runtime_signatures.json`).
- Deliverables: static records (`out/static/field2_records.jsonl`), runtime results (`out/runtime/field2_runtime_results.json`), and merged atlas (`out/atlas/field2_atlas.json`, `out/atlas/summary.json`).

## Outputs (current)
- `out/static/field2_records.jsonl` — one record per seed with tag IDs, anchors, and system-profile placements for that field2; all seeds present by construction.
- `out/runtime/field2_runtime_results.json` — one entry per seed, each tagged to a concrete runtime scenario (profile, operation, expected/result, scenario_id). Seeds without a candidate would be marked explicitly, but the current slice has one probe per seed.
- `out/atlas/field2_atlas.json` — static + runtime merged per field2 with a coarse status (`runtime_backed` vs `static_only`/`no_runtime_candidate`).
- `out/atlas/summary.json` — counts by status to show field2 coverage at a glance.

## Status
- Static: `ok` for the seed slice (anchors + system profiles present for 0/5/7).
- Runtime: **partial** — reuses existing runtime signatures (mach path/global/local and path_edges) and tags each to a seed; no new harness runs yet. All three baseline seeds are `runtime_backed`; the extra static-only seed is marked `no_runtime_candidate`.
- Atlas: `runtime_backed` for baseline seeds, `no_runtime_candidate` for the static-only add-on; will expand if we add seeds or new probes.

## Case studies (seed slice)
- Field2 0 (`path`): Appears on path-centric tags in `sys:sample` and multiple probes; anchors include `/etc/hosts` and `/tmp/foo`. Runtime scenario `field2-0-path_edges` targets path edges (file-read*) and currently returns `deny` in the signature set.
- Field2 5 (`global-name`): Present in `sys:bsd` tag 27 and many mach/path probes; anchors include `preferences/logging` and `/etc/hosts`. Runtime scenario `field2-5-mach-global` exercises `mach-lookup` for `com.apple.cfprefsd.agent` and returns `allow`.
- Field2 7 (`local`): Present in `sys:sample` tags 3/7/8 and network/mach probes; anchors include `/etc/hosts` and blocked `flow-divert`. Runtime scenario `field2-7-mach-local` hits `mach-lookup` for the same name with a local-mode probe and returns `allow`.
- Field2 1 (`mount-relative-path`): Added as a nearby static-only neighbor (same ops/profiles as seed0). Anchored via `/etc/hosts` and present in `sys:sample` tag 8; no runtime probe yet (`no_runtime_candidate`).

## Evidence & artifacts
- Seeds: `book/experiments/field2-atlas/field2_seeds.json`
- Static: `book/experiments/field2-atlas/out/static/field2_records.jsonl`
- Runtime: `book/experiments/field2-atlas/out/runtime/field2_runtime_results.json`
- Atlas: `book/experiments/field2-atlas/out/atlas/{field2_atlas.json,summary.json}`
- Helpers: `atlas_static.py`, `atlas_runtime.py`, `atlas_build.py`; guardrail `book/tests/test_field2_atlas.py`.

## Next steps
- Run the runtime wrapper against fresh probes as they appear (mark `blocked`/`deny` explicitly).
- Decide whether to keep the atlas as a fixed exemplar (0/5/7) or add a small second batch with the same field2-first framing and tests.
