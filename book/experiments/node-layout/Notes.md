# Node Layout Experiment – Running Notes

## 2025-11-27 1

- Baseline blob: `book/examples/sb/build/sample.sb.bin` (583 bytes). Heuristic slices:
  - op_count=9 → op-table length 18 bytes (offset 0x10..0x21).
  - nodes: ~395 bytes.
  - literals/regex: starts at offset ~0x1ad (429), length ~154 bytes. Literal tail shows strings: `/etc/hosts`, `usr`, `dev`, `system`, `/tmp/sb-demo`.
- Quick stride scan on node region:
  - stride 8: tags {0,1,2,3,5,7,8}, all edges in-bounds (interpreting two u16 edges), distinct edges ~6.
  - stride 12: tags {0,3,5,7,8}, edges in bounds 63/64, distinct edges ~8.
  - stride 16: tags {1,3,7,8}, edges in bounds 48/48, distinct edges ~3.
  - 12-byte stride looks promising: more tags than 16, fewer junk tags than 8; edge fields mostly small/bounded.
- Sample record dump @stride=12 (fields: tag, edge1, edge2, literal_idx?, extra):
  - (0, 8, 8, 7, 8, extra=08000700)
  - (1, 7, 7, 8, 8, 08000500)
  - (2, 5, 5, 5, 8, 08000700)
  - (3, 8, 3, 3, 3, 03000300)
  - … many records with tags 7/8 and edges 7/8; occasional literals 1/2 near later records.
  - Offsets suggest: byte0=tag, bytes2-3=edgeA, bytes4-5=edgeB, bytes6-7=literal/regex index candidate.
- Literal region starts at offset 429; many node records show lit index 8 or 3. Need a variant profile to see lit index changes.
- Next steps (not yet done):
  - Compile minimal SBPL variants (single operation; add one `subpath` literal, then change literal) to diff node bytes and confirm which field is the literal index.
  - Automate scoring over strides/fields; check that literal field points into literal pool (index×? lands near `/tmp/...` offsets).
  - Apply candidate layout to `airlock.sb.bin`/`bsd.sb.bin` to see if stride/tag pattern holds and if edges stay in bounds.

## 2025-11-27 2

- Created minimal SBPL variants under `book/experiments/node-layout/sb/`:
  - `v0_baseline`: allow `file-read*` only.
  - `v1_subpath_foo`: allow `file-read*` with `(subpath "/tmp/foo")`.
  - `v2_subpath_bar`: same with `/tmp/bar`.
  - `v3_two_filters`: `(require-all (subpath "/tmp/foo") (subpath "/dev"))` on `file-read*`.
- Compiled with `sandbox_compile_string`:
  - v0 len=440, ops=5, nodes=387, literals=27.
  - v1/v2 len=467, ops=6, nodes=365, literals=74.
  - v3 len=440, ops=5, nodes=387, literals=27.
- Stride=12 node slices:
  - v1 vs v2: node regions are identical (no differing records), so changing literal from `/tmp/foo` to `/tmp/bar` did not change node bytes (literal table differs; literal pool contains `/tmp/foo` in v1). Suggests literal indices may be encoded elsewhere or nodes reference a shared literal index that didn’t change across these two strings.
  - v0 vs v1: 31 records differ; op_count increases (5→6) and literals grow. Indicates adding a `subpath` filter changes node region but not in a way that distinguishes foo vs bar.
  - v0 vs v3: 2 differing records; both have same op_count (5). Diffs show only literal index changes (e.g., record 2 lit 3→4) and tag change in record 3 (3→4). Hypothesis: adding a second filter tweaks literal indices but keeps node count constant when op_count unchanged.
- Literal pools:
  - v0/v3 literals are short, no path strings visible (pure metadata?).
  - v1 literals contain `/tmp/foo`; v2 literals contain `/tmp/bar`. Node bytes unchanged between v1 and v2, so literal index field at bytes6-7 may be a small ID independent of the literal table position, or the literal pool order is fixed and both literals share the same index bucket.
- Open questions:
  - How to map literal indices to actual offsets; current heuristic doesn’t link node field to literal pool address.
  - Whether a different filter type or additional literal would change the node bytes enough to isolate the literal index field.
- Next steps:
  - Add a profile with two distinct literals for the same filter type (e.g., two subpaths) to see if node records diverge.
  - Try stride 8/16 again on v1/v2 to see if any field changes with foo→bar.
  - Consider parsing the op-table entrypoints to anchor which records belong to which operation.

## 2025-11-27 3

- Added open questions to Plan.md (literal index mapping, multiple literals, filter key location, op-table anchoring).
- Still need a variant with two distinct literals in the same profile to force literal index differences; current v1 vs v2 suggests literal field isn’t simply “literal pool offset.”
- Possible next probes:
  - Profile with `(allow file-read* (require-any (subpath "/tmp/foo") (subpath "/tmp/bar")))`.
  - Profile with different filter types (e.g., `literal` vs `subpath`) to see if tag or field changes more clearly.
  - Use op-table entrypoints to segment node array per operation and see if edge fields line up with op_count changes (5→6).

## 2025-11-27 4

- Added variants:
  - `v4_any_two_literals`: `(allow file-read* (require-any (subpath "/tmp/foo") (subpath "/tmp/bar")))`.
  - `v5_literal_and_subpath`: `(allow file-read* (require-all (literal "/etc/hosts") (subpath "/tmp/foo")))`.
- Compiled all variants with `sandbox_compile_string`:
  - v4: len=481, ops=6, nodes=403, lits=50.
  - v5: len=440, ops=5, nodes=387, lits=27.
- Diffs:
  - v1 (`/tmp/foo`) vs v4 (foo+bar): node region lengths differ (365 vs 403) but **no differing records** when comparing common prefix; literal pool differs (contains both foo/bar). Suggests added literals/operators are appended beyond the smaller node array; shared prefix identical. Literal index still not visible in shared records.
  - v1 vs v5 (literal + subpath): 30 differing records, node length increases to 387. This profile introduces a `literal` filter and keeps op_count at 5; indicates new nodes inserted for the extra filter type.
  - v0 (baseline) vs v5: only 2 differing records; both node arrays 387 bytes. Adding `(literal "/etc/hosts")` + subpath without increasing ops tweaks a couple of records (likely the filter nodes) but not the whole shape.
  - v1 vs v2 (foo vs bar): still identical nodes; literal pool differs.
  - v1 vs v4 literal pools: v4 shows `/tmp/foo` and `/tmp/bar` strings; nodes unchanged in shared prefix.
- Observations:
  - Literal strings move into the pool, but node fields for shared regions remain unchanged. Likely literal references are via IDs or the differing nodes live beyond the shorter node array (v4 has extra nodes after the shared prefix).
  - Tag/edge pattern at stride 12 still plausible; need to segment nodes per operation using op-table entrypoints to see which records are new for the added filter(s).
- Next steps:
  - Use op-table entrypoints (first 9 u16s) to derive entry node indices and map which node ranges are actually used by each operation; compare v1 vs v4 in the non-shared tail.
  - Add a variant with two different filter types on the same op but keeping op_count constant, then diff with op-table-aware segmentation.
  - Write a small analyzer to list op-table entries and dump per-op node slices for comparison across variants.

## 2025-11-27 5

- Wrote a quick diff/analyzer to compare node records at stride 12 and to dump op-table entries.
- Diff results:
  - v1 (`/tmp/foo`) vs v4 (foo+bar) still shows zero differing records in the shared prefix; node lengths differ (365 vs 403 bytes), suggesting extra nodes beyond the shared range. Node lengths are not multiples of 12, reinforcing that stride might be an approximation or that trailing data is partial.
  - v1 vs v5 (literal+subpath) shows many differing records in the prefix (first 20 diffs all in early records), indicating that introducing a literal filter changes node records even when op_count stays at 5.
  - v0 vs v5 shows only 2 differing records despite identical node lengths; adding literal+subpath tweaks a couple of nodes when starting from the baseline.
- Op-table entries for all variants are uniform:
  - v0/v5: op_count=5, op entries [4,4,4,4,4].
  - v1/v4: op_count=6, op entries [5,5,5,5,5,5].
  This suggests entrypoints are consistent across ops in a profile and may simply index the first node; does not help segment nodes per op yet.
- Observations:
  - Literal pool contents differ as expected (v4 pool has both foo/bar; v5 pool minimal), but node fields in the shared prefix don’t reflect literal changes.
  - Non-multiple-of-stride node lengths hint that either stride≠12 or the node region includes variable-length/trailer data; need to reconsider stride or allow for trailing metadata.
- Next steps:
  - Examine the extra tail nodes in v4 beyond the v1 length to see if literal references live there.
  - Revisit stride assumption: test 8/16 on new variants and check how many full records fit; consider that records might not be fixed-size.
  - Use op-table entry 4/5 as a starting index to walk nodes (if tags can be interpreted as branch/terminal) to see which nodes are reachable per op.
- Tail inspection (v1 vs v4):
  - v1 has 30 full 12-byte records + 5-byte tail; v4 has 33 full records + 7-byte tail. Extra v4 records include a tag0 record with edges (1,4) and a record with an out-of-bounds edge value (3584), plus partial trailing bytes. This casts doubt on fixed 12-byte stride and suggests variable-length or packed structures; stride may still be a useful approximation for the front of the node array but not the tail.
## Narrative

Started by slicing the existing `sample.sb.bin` to establish a baseline: the heuristic split yields a small op-table, a ~395-byte node region, and a literal tail with obvious strings; stride=12 looked most promising for node records. Generated minimal SBPL variants to force controlled changes: a baseline allow-only profile, single subpath (`/tmp/foo`), same subpath with `/tmp/bar`, and a two-filter require-all. Compiling these showed op_count bumps and node/literal size changes; stride-based diffs revealed that changing foo→bar didn’t alter node bytes, while adding filters did. Added more targeted variants (require-any with two subpaths; literal+subpath) to tease out literal and filter key fields. The two-subpath variant lengthened the node region but kept the shared prefix identical; literal pools differed. Adding a literal filter introduced more node differences. Literal strings reliably appear in the pools, but the node fields referencing them remain opaque in shared regions. Plan is to use op-table entrypoints to map nodes to operations and compare non-shared tails, and to probe mixed filter types further. Throughout, kept notes of stride/tag patterns and the need for a small analyzer to automate per-op slicing and scoring.

## Narrative (Chat)

We began by taking a careful “first cut” through `sample.sb.bin`, using the existing heuristic to separate the op-table, node region, and literal tail. That initial pass already showed the essential structure the substrate promises: a compact operation pointer table, a dense block of policy nodes, and a trailing pool of human-readable strings like `/etc/hosts` and `/tmp/sb-demo`. A quick stride analysis over the node region suggested that treating each node as a 12-byte record produced a small, stable set of tag values and in-bounds successor indices, which made stride=12 a reasonable working hypothesis for the node layout.

To probe the layout, we then constructed a series of tiny SBPL profiles that differed in exactly one respect: a baseline profile that simply allows `file-read*`, a version that adds a single `(subpath "/tmp/foo")` filter, a clone that flips the literal to `/tmp/bar`, and another that uses `(require-all (subpath "/tmp/foo") (subpath "/dev"))`. Compiling these with `sandbox_compile_string` and comparing node regions showed that adding filters changes the node bytes and op-count, while changing `/tmp/foo` to `/tmp/bar` leaves the node bytes identical but alters the literal pool. This pattern told us that literals clearly live in the pool, but the node fields that refer to them are not obviously tied to the literal’s raw position.

From there, we introduced more focused variants to stress “multiple literals” and “mixed filter types”: a profile that uses `require-any` over two subpaths (`/tmp/foo` and `/tmp/bar`), and one that combines a `literal "/etc/hosts"` with a `subpath "/tmp/foo"` in a `require-all`. The require-any profile increased the node region length but kept the shared prefix identical with the single-subpath case, while the literal+subpath profile changed a slice of records without altering op-count. Across all of these, the literal pools evolved exactly as expected—new strings appeared where they should—but the node bytes in the shared regions remained opaque, reinforcing the idea that node fields likely hold compact IDs rather than raw literal offsets.

Taken together, these steps give us a progressively tighter picture of the graph layout: we have a plausible stride, a sense of how adding filters and literals perturbs the node region, and confirmation that literal tables behave as a separate pool. The remaining work is to anchor nodes to specific operations via the op-table, examine the non-shared tails where new filters live, and build a small analyzer that can systematically test candidate field layouts for tags, edges, filter keys, and literal indices across all these controlled variants.
