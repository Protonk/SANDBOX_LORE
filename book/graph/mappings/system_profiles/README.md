# System profiles

Canonical system-profile digests live here.

Current artifact:
- `digests.json` – Per-profile digest (op-table buckets, tag counts, literal sample, sections, validation) for curated system blobs (`airlock`, `bsd`, `sample`) on this host/build.

Role in the substrate:
- These digests are compact, decoder-backed views of real platform **Profile layers** and their compiled **PolicyGraphs**. They provide stable examples of op-table shapes, tag distributions, and literal content for system Seatbelt profiles.
- Other experiments (op-table, tag-layouts, anchors, field2) treat these as ground-truth reference profiles when checking structural hypotheses, and the textbook uses them as worked examples of how SBPL templates, entitlements, and containers manifest in compiled policy.
