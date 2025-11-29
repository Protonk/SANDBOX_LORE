# Anchor mappings

Stable anchor-derived mappings live here.

Current artifacts:
- `anchor_field2_map.json` – Anchor → `field2` hints derived from `probe-op-structure` anchor hits. Each anchor is a human-meaningful literal (path, mach name, iokit class) that the experiments have tied to one or more `field2` values and node indices.
- `anchor_filter_map.json` – Anchor → Filter-ID/name map (confidence varies by anchor; see `status` fields; includes host metadata). This file interprets the `field2` hints using the Filter Vocabulary Map and expresses anchors directly in terms of Filters.

Role in the substrate:
- Anchors come from SBPL- or profile-level literals (paths, mach names, etc.) and serve as stable “handles” for specific filters in the PolicyGraph.
- Together these maps connect the **literal world** (file paths, mach names) to **Filter** semantics and `field2` encodings, which is essential when reconstructing SBPL-style rules from compiled profiles or building capability catalogs around concrete resources.
