# bsd-airlock-highvals

## Purpose

Track and retire the remaining high/opaque `field2` payload clusters tied to platform profiles: the `sys:bsd` tag 26 payloads (`174/170/115/109`) plus the tag-0 hi-bit tail (`16660`), and the `sys:airlock` highs (`165/166/10752`) and sentinel-like values (`65535/3584`). The goal is to turn these from “opaque payloads in static decodes” into characterized or anchored mappings that can feed atlas/carton and guardrails without destabilizing validated mappings.

## Baseline & scope

- Host/world: `sonoma-14.4.1-23E224-arm64-dyld-2c0602c5` (project baseline).
- Scope: static compile/decode first; runtime only if needed and feasible. No cross-version claims.

## Prior evidence (static)

- `field2-filters` census and reports contain the canonical sightings and context: [../field2-filters/Report.md](../field2-filters/Report.md), [../field2-filters/Notes.md](../field2-filters/Notes.md), [../field2-filters/Manual-Ghidra.md](../field2-filters/Manual-Ghidra.md), [../field2-filters/out/unknown_nodes.json](../field2-filters/out/unknown_nodes.json), and [../field2-filters/out/field2_inventory.json](../field2-filters/out/field2_inventory.json).
- Tag-layout probing notes the same highs and stride ambiguity for tag 26: [../probe-op-structure/Report.md](../probe-op-structure/Report.md), [../probe-op-structure/out/tag_layout_assumptions.json](../probe-op-structure/out/tag_layout_assumptions.json).
- Literal-bearing tag inventories include these payloads: [../tag-layout-decode/out/tag_literal_nodes.json](../tag-layout-decode/out/tag_literal_nodes.json).
- System profile digests/decodes showing occurrences: [../system-profile-digest/out/digests.json](../system-profile-digest/out/digests.json), [../golden-corpus/out/decodes/platform_airlock.json](../golden-corpus/out/decodes/platform_airlock.json).
- Anchor map currently lacks bindings for these highs (or lists them as unknown): [../anchor-filter-map/Report.md](../anchor-filter-map/Report.md).

## Prior attempts and dead ends

- Targeted SBPL probes aimed at `bsd` literals failed to surface the high payloads outside the full profile: [../field2-filters/sb/bsd_tail_context.sb](../field2-filters/sb/bsd_tail_context.sb), [../field2-filters/sb/dtracehelper_posixspawn.sb](../field2-filters/sb/dtracehelper_posixspawn.sb) (with and without extra mach rules). Decodes showed only low vocab IDs.
- `field2-filters` hi/lo census shows `16660` (`0x4114`) as hi-bit (`0x4000`) tail on tag 0 with broad op reach (ops 0–27), and tag-26 highs `174/170/115/109` as op-empty leaves. Airlock highs stay confined to ops around `system-fcntl` (e.g., sentinel `0xffff` in `airlock_system_fcntl`), with no anchor binding.
- Kernel immediate searches for key constants (0xa00, 0x4114, 0x2a00) returned zero hits: see `kernel_imm_search` notes in [../field2-filters/Notes.md](../field2-filters/Notes.md).
- Tag-26 stride remains ambiguous between 12 and 16 bytes; high payloads appear under both assumptions but layout is unresolved: [../probe-op-structure/Notes.md](../probe-op-structure/Notes.md).

## Deliverables / expected outcomes

- A focused probe matrix (SBPL → compiled blobs → decodes) that can either reproduce or exclude these payloads under controlled variants (especially tag 26 paths for `bsd` and tag 166/1 scaffolding for `airlock`).
- Normalized inventories under `out/` (e.g., decoded node records, unknown/high payload slices) joinable against existing field2 census for cross-checks.
- A characterization or anchor-binding proposal (if found) that can be promoted into atlas/guardrails without hand-editing stable mappings.
- Clear blockers if the values remain opaque (e.g., layout ambiguity, compile gating).

## Plan & execution log

- ✅ Initialize experiment scaffold.
- Next: design probe matrix for `bsd` tag 26 and tag-0 tail (vary literals, ops, and rule shapes) and for `airlock` high tags (system-fcntl variations, minimal scaffolding).
- Next: decode and compare against existing inventories to detect reproduction or absence.
- Later: attempt anchor/field2 joins and, if justified, propose characterization for atlas/guardrails.

## Evidence & artifacts

- `out/` – will hold decoded inventories and probe outputs (to be populated).
- `sb/` – SBPL probes for `bsd`/`airlock` variants (to be authored).
- Upstream references: inventories and reports linked above.

## Blockers / risks

- `sys:airlock` apply/runtime gates limit runtime witnesses; static-only paths must suffice.
- Tag-26 layout ambiguity (stride 12 vs 16) can distort edge/fan-out interpretation until resolved.
- High payloads may be tightly coupled to full platform profiles; simplified SBPL may fail to reproduce them, risking false negatives.

## Next steps

- Draft SBPL probes targeting `bsd` tag-26-like constructs and tail reachability; compile/decode and compare payloads.
- Draft SBPL probes for `airlock` high tags around `system-fcntl`, varying rule shapes and literals.
- If reproduction succeeds, derive characterization constraints; if not, bound the negative results and revisit layout/anchor angles.
