# Tag layouts

Literal/regex tag layout mappings live here.

Current artifact:
- `tag_layouts.json` – Best-effort per-tag layout description (record size, edge fields, payload fields) for tags that carry literal/regex operands, derived from canonical profiles on this host/build.

Role in the substrate:
- In Concepts, a **Policy node** has a tag, edge fields, and payload fields; some payloads carry indices into the literal or regex tables. This file records those layouts for the tags we have evidence for.
- The decoder (and other tools) use these layouts to interpret node fields as “follow this edge” vs “use this literal/regex operand,” which is necessary to reconstruct Filters and Metafilters from raw node bytes and to keep the PolicyGraph view consistent across experiments.
