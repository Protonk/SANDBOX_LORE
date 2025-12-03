# Field2 ↔ Filter Mapping (Sonoma 14.4.1, Apple Silicon)

## Goal
Anchor the third node slot (`filter_arg_raw` / “field2”) in compiled PolicyGraphs to concrete Filter vocabulary entries on this host. Use static decoding plus SBPL probes to turn unknown/high values into evidence-backed mappings and to bound what we do **not** know.

## Baseline & evidence backbone
- Host: macOS 14.4.1 (23E224), Apple Silicon, SIP enabled.
- Canonical vocab: `book/graph/mappings/vocab/{filters,ops}.json` (status: ok).
- Canonical profiles: `book/examples/extract_sbs/build/profiles/{bsd,airlock,sample}.sb.bin`.
- Core outputs: `out/field2_inventory.json` (histograms + hi/lo/tag counts) and `out/unknown_nodes.json` (hi/unknown nodes with fan-in/out and op reach).
- Tooling: `harvest_field2.py`, `unknown_focus.py`, Ghidra scripts under `book/api/ghidra/scripts/` (notably `find_field2_evaluator.py`).

## What we know (evidence)
- **Low IDs match vocab**: `bsd` and `sample` map path/socket/iokit filters as expected (e.g., 0=path, 1=mount-relative-path, 3=file-mode, 5=global-name, 6=local-name, 7=local, 8=remote, 11=socket-type, 17/18 iokit, 26/27 right-name/preference-domain, 80 mac-policy-name).
- **High/unknown clusters** (hi=0 unless noted):
  - `flow-divert` literal → `field2=2560` (lo=0xa00) only when socket-domain + type + protocol are all required (mixed probes v4/v7 and `net_require_all_domain_type_proto`); op reach empty.
  - `bsd` tail → `field2=16660` (hi=0x4000, lo=0x114) on tag 0, reachable from ops 0–27 (default/file* cluster). Other bsd highs 170/174/115/109 live on tag 26, op-empty.
  - `airlock` → 165/166/10752 on tags 166/1/0, attached to op 162 (`system-fcntl`).
  - New probe sentinel → `field2=0xffff` (hi=0xc000, lo=0x3fff) in `airlock_system_fcntl` probe on tag 1, no literals.
  - `sample` sentinel → 3584 (lo=0xe00) on tag 0, op-empty.
- **Ghidra (arm64e sandbox kext `/tmp/sandbox_arm64e/com.apple.security.sandbox`)**
  - Helper hunt now prefers `__read16` at `fffffe000b40fa1c`: bounds checks + `ldrh/strh`, no masking. `__read24` (halfword+byte) still used elsewhere.
  - `_eval` at `fffffe000b40d698` masks on 0x7f / 0xffffff / 0x7fffff and tests bit 0x17; no `0x3fff`/`0x4000` masks found. Dumped in `dumps/ghidra/out/14.4.1-23E224/find-field2-evaluator/`.
  - No hits for 0x3fff/0x4000 in evaluator path; earlier mask scans also negative.

## Recent probes & inventories
- Added `sb/bsd_ops_default_file.sb` (ops 0,10,21–27) → only low path/socket IDs + 3584 sentinel; no bsd highs.
- Added `sb/airlock_system_fcntl.sb` (system-fcntl + fcntl-command) → mostly low path/socket IDs + new 0xffff sentinel.
- Inventories refreshed (`harvest_field2.py`, `unknown_focus.py`); op reach now included for unknowns.

## Open questions
- Where (if anywhere) are hi/lo bits of field2 interpreted? Current evaluator dump shows no 0x3fff/0x4000 masking.
- What semantics drive the bsd tail high (16660) and the airlock highs (165/166/10752) and the new 0xffff sentinel?
- Can flow-divert 2560 be tied to a specific filter or tag pattern beyond “triple socket predicates + literal”?

## Next steps (handoff-ready)
1) **Evaluator validation**: Revisit `_eval` and adjacent helpers to confirm no hidden masking; if needed, dump specific call sites that consume `__read16` results (e.g., `_populate_syscall_mask`, `_match_network`) to ensure field2 stays raw.
2) **Targeted probes by op reach**:
   - Bsd highs: craft profiles that keep ops 0–27 but alter literals/structure to see if 16660/170/174/115/109 can surface outside the full bsd blob.
   - Airlock highs: vary `system-fcntl` filters/arguments to chase 165/166/10752/0xffff; look for literals or edge shapes that bind them.
   - Flow-divert: minimally perturb the triple-socket shape (order, default decisions, require-all vs any) to see if 2560 reachability changes or gains op links.
3) **Mapping hygiene**: Keep hi/lo split (`field2_hi = raw & 0xc000`, `field2_lo = raw & 0x3fff`) in all outputs; do not coerce unknown/high values into vocab. Record op reach and tag context for every new unknown.
4) **Guardrails (later)**: Once any high value gets a plausible binding with static + evaluator evidence, add a small regression check (script or note) before promoting to a shared mapping.

## Artifacts index
- Inventories: `book/experiments/field2-filters/out/field2_inventory.json`, `out/unknown_nodes.json`.
- Probes: `sb/` sources and `sb/build/*.sb.bin` (including new `bsd_ops_default_file` and `airlock_system_fcntl`).
- Ghidra: `dumps/ghidra/out/14.4.1-23E224/find-field2-evaluator/` (`field2_evaluator.json`, `helper.txt`, `eval.txt`, `candidates.json`).
- Scripts: `harvest_field2.py`, `unknown_focus.py`, `book/api/ghidra/scripts/find_field2_evaluator.py`.

## Risks & constraints
- High values remain sparse and op-empty (except bsd 16660); false positives from generic scaffolding are likely in tiny probes.
- Tag layouts for higher tags (26/27/166) are only partially understood; keep edge-field assumptions aligned with `book/graph/mappings/tag_layouts/tag_layouts.json`.
- Runtime/application of platform blobs is gated; all findings are static unless explicitly validated elsewhere (none yet for these highs).
