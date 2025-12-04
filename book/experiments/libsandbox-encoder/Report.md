## Purpose

Map how this host’s `libsandbox` encodes filter arguments into the `field2` u16 in compiled profiles and align those encodings with the Filter Vocabulary Map (`book/graph/mappings/vocab/filters.json`, status: ok). The kernel is treated as consuming a raw u16; the focus here is purely on userland emission.

## Baseline & scope

- Host: macOS 14.4.1 (23E224), Apple Silicon, SIP enabled (`book/world/sonoma-14.4.1-23E224-arm64/world-baseline.json`).
- Inputs: `book/api/sbpl_compile`, `book/api/decoder`, trimmed `libsandbox` slice under `book/graph/mappings/dyld-libs/`.
- Out of scope: runtime `sandbox_apply` or kernel-side interpretation (covered by `field2-filters`).

## Plan & execution log

- Phase A — SBPL→blob matrix (encoder output view): matrix v1 (regex-free) compiled via `sbpl_compile`; nodes parsed via `profile_ingestion` + custom helper with local tag overrides; table emitted to `out/matrix_v1_field2_encoder_matrix.json`. Tag2/tag3 treated as meta/no payload; tag10 resolved header-aligned layout (tag=h0.low, filter_id=h1, payload=h2) via full-context socket-domain 2→30 variants; matrix now exposes both `filter_id_raw` and `payload_raw` for tag10. Tag8 left filter-id-only.
- Phase B — libsandbox internals (encoder implementation view): serializer RE in progress; buffer at builder+0xe98 confirmed; `_emit_network` ordering/widths noted; finalize path to `__sandbox_ms` and explicit store offsets still pending.

## Evidence & artifacts

- `sb/matrix_v1.sb` (regex-free baseline); `sb/matrix_v2.sb` (arg-variance probe; decode currently skewed to tag6/5; not used for conclusions).
- `sb/matrix_v1_domain2.sb`, `sb/matrix_v1_domain30.sb` (full-context copies of matrix_v1 with socket-domain 2 vs 30) used to confirm tag10 payload offset.
- `out/tag_layout_overrides.json` (local, staged) for tags 2/3/8/10; tag10 resolved: tag=h0.low, filter_id=h1, payload=h2 (header-aligned).
- `out/matrix_v1.sb.bin`, `out/matrix_v1.inspect.json`, `out/matrix_v1.op_table.json`, `out/matrix_v1_field2_encoder_matrix.json` (Phase A table with tag2/3 excluded; tag10 includes payload).
- `out/matrix_v2.sb.bin`, `out/matrix_v2.inspect.json`, `out/matrix_v2_field2_encoder_matrix.json` (decode skewed; not relied on).
- `dump_raw_nodes.py` (heuristic node dumper used in Phase B; now also supports `--header` to slice using `inspect_profile`’s `nodes_start`/`nodes_len`). For `matrix_v1.sb.bin` it locates a 12-byte-stride node block at [0,480) and shows the seven records closest to the literal pool as:
  - 396: [0, 0, 2560, 21, 10, 1]
  - 408: [3328, 6, 9, 2, 3072, 1]
  - 420: [9, 3, 2816, 2, 9, 10]
  - 432: [1536, 11, 9, 5, 1792, 16]
  - 444: [9, 10, 4352, 5, 9, 7]
  - 456: [4608, 8, 9, 10, 256, 0]
  - 468: [9, 10, 1281, 0, 0, 0]
- Pending: `out/encoder_sites.json`.

## Blockers / risks

- Phase B is expected to be partial/brittle unless encoder patterns are obvious; no promotion to `book/graph/mappings/*` without corroboration.

## Phase B notes (in-progress)

- Serializer context (manual RE): in the “bytecode_output.c” region (`0x183d01f*`), the compiler sets `x22 = builder + 0xe98` and uses that pointer for `_sb_mutable_buffer_set_minimum_size` and `_sb_mutable_buffer_write`. The same base+0xe98 is passed through `_emit`, `_emit_instruction`, `_emit_pattern`, etc., so offset 0xe98 is the mutable buffer handle for the compiled profile. `_encode_address` also touches `[ctx, #0xe98]` (on overflow it stores an error there), reinforcing that 0xe98 is the buffer field in the builder.
- Finalize/hand-off to `__sandbox_ms` still to be confirmed: need to follow the builder’s finalize path (post `_sb_mutable_buffer_make_immutable`) up to the caller that packages `buf,len` for `__sandbox_ms` to cement “this is the blob we decode”.
- Next mapping task: in `_emit_network`/`_record_condition_data`, watch the write cursor around the three `_emit` calls (domain/type/proto), derive their byte offsets, and align those emitted bytes to the tag10 halfwords we dumped (offsets 398–422) to confirm the payload field (currently h2).
- `_emit_network` disasm skim: pads to 8-byte boundary when needed (`[ctx+8]->0x18 & 7`, then `_emit` zeros of size `(8 - rem)`), calls `_get_current_data_address`, then emits three items in order via `_emit` with sizes {1,1,2} from the arg struct (`ldrb [arg+#1]`, `ldrb [arg]`, `ldrh [arg+#2]`). `_emit` itself writes byte-by-byte to the mutable buffer (`ldr x8, [ctx,#0x8]`, `_sb_mutable_buffer_write(x8, cursor, sp_bytes)`), asserting that the value fits in the requested width (`value < 0x100` for size 1). This gives a concrete “domain/type/proto” write order and confirms the buffer path used by per-filter emitters.
- `_record_condition_data` is a compact linker: it decrements `c->ec_free_count`, uses that index to write a 0x18-byte entry `{data_ptr, data_len?, filter_id}` into the `ec_data` array, and threads the entry into a per-op linked list via `[ctx + (tag?)*8 + 0x20]`. This is likely how filter ID + data offset get paired before serialization.
- Tooling note: `inspect_profile` now emits `nodes_raw` (offset, tag byte, raw bytes, halfwords) to make per-record layouts explicit. `dump_raw_nodes.py` can also read `nodes_start`/`nodes_len` from the adjacent `*.inspect.json` via `--header` (using `nodes_raw` count/size). Phase A matrix now emits both `filter_id_raw` and `payload_raw` for payload-bearing tags (tag10: tag=h0.low, filter_id=h1, payload=h2 confirmed via matrix_v1_domain2/30).
- Encoder sites logged in `out/encoder_sites.json`: `_emit` (bytes→mutable buffer via `_sb_mutable_buffer_write`), `_emit_network` (domain/type/proto via three `_emit` calls), `_record_condition_data` (stores data_ptr/len/index into per-op list), and the mutable buffer handle at builder+0xe98 (partial).
- Finalize path: `_compile` calls `_sb_mutable_buffer_make_immutable` on the builder’s mutable buffer (builder+0xe98) at 0x183ced36c and stores the resulting `sb_buffer*`; explicit handoff of that immutable buffer to `__sandbox_ms` remains to be traced.

## Next steps

- Continue Phase B disassembly: confirm buffer finalize path into `__sandbox_ms`; tie `_emit_network`/`_record_condition_data` offsets to the tag10 payload slot for a code-level provenance.
- Optional follow-up: if needed later, resolve tag8 payload via the same “vary one arg” header-aligned method; currently treated as filter-id-only.
