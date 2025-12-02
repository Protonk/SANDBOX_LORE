# Symbol Search – Research Report (BootKernelExtensions.kc, 14.4.1 / 23E224)

## Purpose

Recover the sandbox PolicyGraph dispatcher and adjacent helpers by leveraging symbol/string pivots (AppleMatch imports, sandbox strings, MACF hook tables) and structural signatures, rather than relying on computed-jump density.

## Baseline and scope

- Host target: macOS 14.4.1 (23E224), Apple Silicon, SIP enabled (same baseline as other Ghidra experiments).
- Artifacts: `dumps/Sandbox-private/14.4.1-23E224/kernel/BootKernelExtensions.kc`, Ghidra project `dumps/ghidra/projects/sandbox_14.4.1-23E224`.
- Tooling: headless Ghidra scripts in `dumps/ghidra/scripts/` (string refs, tag switch, op-table), `scaffold.py` with `--process-existing` to reuse the analyzed project.
- Concept anchors: dispatcher should walk compiled PolicyGraph nodes (two successors, action terminals), consult operation→entry tables, call AppleMatch for regex filters, and sit downstream of MACF hook glue.

## Planned pivots

- String/import searches for AppleMatch helpers and sandbox identifiers, with caller enumeration.
- MACF `mac_policy_conf` / `mac_policy_ops` traversal to find the shared sandbox check helper invoked by `mpo_*` hooks.
- Header/section signature scans using `.sb.bin` fixtures to find embedded profile structures in KC.
- Cross-correlation of the above to nominate dispatcher/action-handling functions for deeper analysis.

## Current observations

- Headless string/import scans (all blocks, customizable queries) surface only the known sandbox/AppleMatch strings and no references or external symbols so far, suggesting AppleMatch imports may use different library labels or be inlined; next step is to enumerate external libraries/imports to refine the filter before proceeding to MACF and structure pivots.
- TextEdit `.sb.bin` decode yields op_count=266, magic word=0x1be, nodes_start=548, literal_start=1132; a straight byte signature of the first 32 header bytes does not appear in the KC, so embedded profiles (if any) likely have different preambles or encodings.
- Pointer-table sweep across all KC blocks produced multiple 512-entry tables in `__desc`/`__const` (starts near 0x-7fffef5000) pointing at sandbox-region functions; these are candidates to cross-check against mac_policy_ops or op-entry tables.
- Raw byte scan for adjacent words `0x10a, 0x1be` in the KC found three code sites (file offsets ~0x1466090, 0x148fa37, 0x14ffa9f), implying these constants surface as immediates in code rather than as embedded profile headers; mapping these to Ghidra addresses may reveal profile parsing paths.
- Offset→address lookup shows those constant sites map into `__text` functions `FUN_ffffff8001565fc4`, `FUN_ffffff800158f618`, `FUN_ffffff80015ff7a8` (likely parsing/loader paths; no callers yet).
- The most promising pointer table is at `__const` 0x-7fffdae120: 512 entries, 333 pointing to `FUN_ffffff8000a5f0b0` (90 unique functions total, few nulls). Initial function info shows this target is a tiny stub (8 bytes, DATA ref only), suggesting the real dispatcher is adjacent (data-driven jump or wrapper). Next: inspect the data reference at `0x-7ffcb08ca4` and nearby functions in the table to identify the actual evaluator/walker.

## Reporting

- `Notes.md`: running log of commands, addresses, and shortlists.
- `Plan.md`: staged steps and stop conditions.
- This report: rationale, baseline, and how each pivot ties back to the Seatbelt concepts (PolicyGraph evaluation, operation vocabulary, sandbox label plumbing).
