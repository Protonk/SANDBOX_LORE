# Symbol Search – Research Report

## Purpose
Locate the sandbox PolicyGraph dispatcher (and helpers) in the KC by combining AppleMatch/sandbox string and import pivots with MACF hook traces and op-table structure checks.

## Baseline & tooling
- Host: `world_id sonoma-14.4.1-23E224-arm64-dyld-2c0602c5` (Apple Silicon, SIP on).
- Inputs: `dumps/Sandbox-private/14.4.1-23E224/kernel/BootKernelExtensions.kc`; analyzed Ghidra project `dumps/ghidra/projects/sandbox_14.4.1-23E224`.
- Tools: `book/api/ghidra/run_task.py` tasks (`kernel-string-refs`, `kernel-data-define`, `kernel-op-table`, etc.), ARM64 processor with `disable_x86_analyzers.py`; repo-local JAVA/HOME/TMPDIR (`JAVA_TOOL_OPTIONS=-Duser.home=$PWD/dumps/ghidra/user -Djava.io.tmpdir=$PWD/dumps/ghidra/tmp`).

## Current status
- Import census: unfiltered `kernel-imports` (imports_all.json) plus filtered view (`filter_imports.py --substr applematch mac_policy sandbox seatbelt`) show 0 matching externals. Import/GOT anchors for these names are ok-negative on this world.
- String sweep: `kernel-string-refs` (clean argv, `extlib=`) yields 190 string hits, 0 symbol hits, 0 externals; all references are LINKEDIT-only. MACF/AppleMatch/sandbox evidence via names is string-table-only and not referenced from code or data.
- Data/XREF probes: `kernel-data-define` on sandbox strings and op-table starts resolves to two strings (no callers) and four pointers to `0xffffff8000100000`; one LINKEDIT data ref at `0x-7ffc3311d0` (no function). `kernel_imm_search` for mac_policy_init and _mac_policy_register string addresses returned 0 hits. No mac_policy_conf/mac_policy_ops struct or mpo_* helper located.
- Op-table context: earlier pointer-table sweeps still show dense 512-entry tables (e.g., `__const` 0x-7fffdae120) but with no recorded callers; linkage to a dispatcher is speculative.

## Findings (status-aware)
- AppleMatch pivot: ok-negative for imports (full census shows no externals); partial/brittle for strings (LINKEDIT-only, no callers).
- mac_policy_conf/mac_policy_ops: blocked — no struct or mpo_* helper resolved; data-define/XREFs were empty and imm-search for key strings returned 0 hits.
- Dispatcher linkage: under exploration — op-table-like tables exist but lack references; no intersection with AppleMatch/mac_policy yet.

## Open questions
- Where are the AppleMatch entry points (imports or stubs) referenced from sandbox code?
- Where is the sandbox mac_policy_conf/mac_policy_ops registered, and what shared helper do the mpo_* hooks call?
- Do the dense pointer tables align with the promoted op-table layout, and if so, how are they reached at runtime?

## Next steps
1) Close this experiment as ok-negative for kernel imports/symbol anchors; keep string-only evidence documented.
2) Spin out a dedicated mac_policy registration experiment (kext-aware) to recover mac_policy_conf/ops and registration sites.
3) Revisit op-table candidates only after a concrete mac_policy_ops candidate exists; align against `book/graph/mappings/op_table/op_table.json` before running table-materialization scans.

## Evidence & artifacts
- Project: `dumps/ghidra/projects/sandbox_14.4.1-23E224`.
- String refs: `dumps/ghidra/out/14.4.1-23E224/kernel-string-refs/string_references.json` (190 hits, no externals).
- Import census: `dumps/ghidra/out/14.4.1-23E224/kernel-imports/imports_all.json` plus filtered `imports_filtered_sandbox.json` (0 matches for applematch/mac_policy/sandbox/seatbelt).
- Data refs: `dumps/ghidra/out/14.4.1-23E224/kernel-data-define/data_refs.json` (sandbox strings + pointer targets, no callers).
- Pointer tables: `book/experiments/kernel-symbols/out/14.4.1-23E224/op_table_candidates.json` (dense tables, unreferenced so far).
