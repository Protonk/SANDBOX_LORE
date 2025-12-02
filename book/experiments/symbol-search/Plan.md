# Symbol Search (sandbox dispatcher and regex callers)

Goal: locate the sandbox PolicyGraph dispatcher and related helpers inside `BootKernelExtensions.kc` by chasing symbol/string references (AppleMatch imports, sandbox strings, MACF hooks) and signature scans instead of raw computed-jump heuristics.

---

## 1) Scope and setup

**Done**

- Scaffolded this experiment directory (Plan, Notes, ResearchReport). Inputs: `dumps/Sandbox-private/14.4.1-23E224/kernel/BootKernelExtensions.kc`, analyzed Ghidra project `dumps/ghidra/projects/sandbox_14.4.1-23E224`, headless scripts under `dumps/ghidra/scripts/`.

**Upcoming**

- Confirm baseline metadata in `ResearchReport.md` (OS/build, SIP, tools).

Deliverables: this plan, `Notes.md`, `ResearchReport.md`; `out/` for scratch JSON listings if needed.

## 2) Expand symbol and string pivots

**In progress**

- Broadened string/import search via `kernel_string_refs.py` (all blocks, custom queries); current runs still return only the core sandbox/AppleMatch strings with no references.
- Next: enumerate external libraries/imports to learn actual AppleMatch naming (if any) and adjust filters; add caller histograms once a viable import/string is found.

Deliverables: refreshed headless outputs under `dumps/ghidra/out/.../kernel-string-refs` (or a new task) with expanded queries and caller counts.

## 3) AppleMatch import pivot

**Upcoming → now guided by web-agent anchors**

- Enumerate Sandbox.kext externals/imports and specifically hunt for AppleMatch exports `_matchExec` / `_matchUnpack` (or close variants). Collect callers.
- Cross-check callers against MACF-hook helpers (shared `(cred, op_id, …)` path) to converge on the PolicyGraph node walker.
- Use caller intersection (AppleMatch import users ∩ op-table indexers) as the primary dispatcher shortlist.

Deliverables: shortlists of AppleMatch callers plus addresses/functions, with notes in `Notes.md`.

## 4) MACF hook and mac_policy_ops pivot

**Upcoming → paired with AppleMatch pivot**

- Locate the sandbox `mac_policy_conf`/`mac_policy_ops` struct; trace `_mpo_*` entries into the shared helper (`cred_sb_evaluate`/`sb_evaluate_internal`-like).
- Follow that helper into the inner `eval`-like routine that indexes an op-entry table and walks nodes; intersect with AppleMatch caller set to validate dispatcher identity.

Deliverables: function addresses and linkage notes tying MACF hooks to the dispatcher, logged in `Notes.md`.

## 5) Profile structure pivot

**In progress**

- Parsed TextEdit `.sb.bin`: op_count=266, magic word=0x1be, nodes_start=548, literal_start=1132; initial 32-byte header signature not found in KC via raw byte search.
- Next: build a more flexible signature (multiple word positions) and scan KC via headless script to surface embedded profiles, then look for code that walks those structures.
- Added `kernel_page_ref_scan.py` to hunt for ADRP/ADD references into the suspected 512-entry table at `0xffffff8000251ee0`; first pass (all blocks) reported 0 hits, so a follow-up variant that decodes ADRP immediates without pre-existing references is needed.
- x86-style page scans against the same address show nothing (as expected on ARM64). De-prioritize this address as the op table until ARM64-specific evidence (ADRP+ADD/LDR or profile-walker usage) surfaces; focus on ARM patterns and profile-anchored signatures.
- Data/constants pivot:
  - Found one little-endian instance of the suspected table pointer at file offset `0x52978` (addr `0xffffff8000152978` in `__desc`); defining it and collecting xrefs yielded no callers (still undefined data).
  - ARM const-base scan (`kernel_arm_const_base_scan.py`) over `0xffffff8000250000–0xffffff8000260000` saw 0 ADRP and 0 matches, suggesting Ghidra isn’t decoding ADRPs in sandbox text. Next steps for future agent: improve ADRP detection or run a profile-header signature scan to find embedded blobs, then chase code that walks them.

Deliverables: signature JSON in `out/` if needed, plus scan results with candidate addresses.

## 6) Synthesis and stop condition

**In progress**

- Cross-link AppleMatch callers (none yet), MACF hook helpers, profile-structure scans, and the new pointer-table results. Current strongest lead: 512-entry table at `__const` 0x-7fffdae120 pointing 333 times to `FUN_ffffff8000a5f0b0` (candidate op-entry dispatcher target). Also have three code sites with op_count/magic constants mapping to `FUN_ffffff8001565fc4`, `...158f618`, `...15ff7a8`.
- `FUN_ffffff8000a5f0b0` appears to be a tiny stub (8 bytes, single DATA reference). Next pivot: examine the data reference at `0x-7ffcb08ca4` and nearby functions in the table (e.g., top unique targets) to locate the real dispatcher/action walker.
- Disassembly dumps for the op-count/magic sites show prolog-heavy routines populating structs and calling helpers (e.g., `0xffffff80016c4a16`, `0xffffff80015aaf56`, `0xffffff8002fd0f5e`) but no obvious op-table indexing yet; need to trace those callouts and any adjacency to the pointer tables.
- Stop when one or more functions are consistently referenced across pivots and show node-array walking with two successors and action handling.

Deliverables: summary in `ResearchReport.md` of evidence-backed dispatcher candidates and recommended next probes.
