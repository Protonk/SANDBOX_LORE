# Symbol Search – Notes

Use this file for dated, concise notes on commands, findings, and pivots.

## 2025-12-30

- Scaffolded experiment (Plan/Notes/ResearchReport). Ghidra inputs: analyzed project `dumps/ghidra/projects/sandbox_14.4.1-23E224`, headless scripts in `dumps/ghidra/scripts/`. Next actions: widen string/import queries and collect caller maps.

## 2025-12-31

- Extended `kernel_string_refs.py` to accept extra args (`all`, `extlib=...`, `symsub=...`) and to run against existing projects via `--process-existing` scaffold flag.
- Runs (no-analysis, reuse project):
  - `all` blocks, defaults → 3 string hits (`AppleMatch`, two sandbox strings), 0 symbol hits, 0 externals.
  - `all extlib=match symsub=match` → same 3 strings, still 0 symbol hits / externals. No references recorded to those strings.
- External library summary is empty (Ghidra reports no external symbols in the KC import table), so the AppleMatch-import pivot needs a different approach (e.g., MACF hook trace or structure signature).
- Conclusion: direct string/import pivots are dry so far; need to enumerate external libraries/imports to adjust filters or pivot to MACF/profile signatures.

## 2025-12-31 (later)

- Parsed TextEdit `.sb.bin` via `book.api.decoder.decode_profile`: op_count=266 (0x10a), magic word=0x1be, early header words `[0, 266, 446, 0, 0, 6, 0, 36, 398, 1113, 1070, ...]`, nodes_start=548, literal_start=1132. Raw 32-byte header signature (little endian) not found in `BootKernelExtensions.kc` via direct byte search.
- Expanded `kernel_op_table.py` to allow `all` blocks; reran headless with `--process-existing --script-args all`. Found 224 pointer-table candidates; largest runs length=512 at `__desc` and multiple `__const` offsets (e.g., start 0x-7fffef5000). First entries point to functions like `FUN_ffffff80003be400`, `FUN_ffffff8000102800`, with many null/unknown targets, suggesting generic function-pointer tables (possible mac_policy_ops candidate to inspect).
- Searched KC bytes for adjacent little-endian words `0x10a, 0x1be`; found three code sites at file offsets 0x1466090, 0x148fa37, 0x14ffa9f (surrounding bytes look like instructions). These constants might appear in profile-parsing paths rather than embedded profile data; need address mapping in Ghidra to inspect callers.

## 2026-01-01

- Added headless `kernel_addr_lookup.py` to map file offsets to addresses/functions/callers; scaffold supports `kernel-addr-lookup`.
- Looked up offsets {0x1466090, 0x148fa37, 0x14ffa9f}: map to `__text` functions `FUN_ffffff8001565fc4`, `FUN_ffffff800158f618`, `FUN_ffffff80015ff7a8` (no instruction bytes retrieved yet; likely need disassembly pass). No callers recorded.
- Pointer table deep-dive: 512-entry table at `__const` start `0x-7fffdae120` has 333 entries pointing to `FUN_ffffff8000a5f0b0` (90 unique functions total, 27 nulls). Other 512-entry tables: `__desc` start `0x-7fffef5000` (4 funcs total) and `__const` start `0x-7fffddf830` (12 funcs). The dense table with a dominant single target looks like a strong op-entry pointer table candidate; target function is the next analysis focus.
- Added `kernel_function_info.py` to dump callers/callees for a named function; run on `FUN_ffffff8000a5f0b0` shows: address `0x-7fff5a0f50` (`__text`), size 8 bytes, one DATA reference from `0x-7ffcb08ca4`, no callees. This suggests `FUN_ffffff8000a5f0b0` is likely a tiny stub (perhaps start of a jump table) rather than the evaluator proper; need to inspect surrounding data/callers.
