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

