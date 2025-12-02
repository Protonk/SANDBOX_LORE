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

**Upcoming**

- Enumerate external imports in sandbox.kext that resolve to AppleMatch and collect their callers; flag callers that also index shared arrays or branch on tag-like values.
- Note any adjacency to regex/literal data structures recovered from `.sb.bin` fixtures.

Deliverables: shortlists of AppleMatch callers plus addresses/functions, with notes in `Notes.md`.

## 4) MACF hook and mac_policy_ops pivot

**Upcoming**

- Locate the sandbox `mac_policy_conf`/`mac_policy_ops` struct; trace `mpo_*` entries into shared helpers.
- Identify the common helper that accepts a label/policy pointer and operation ID, and follow it into the graph-walk candidate set.

Deliverables: function addresses and linkage notes tying MACF hooks to the dispatcher, logged in `Notes.md`.

## 5) Profile structure pivot

**In progress**

- Parsed TextEdit `.sb.bin`: op_count=266, magic word=0x1be, nodes_start=548, literal_start=1132; initial 32-byte header signature not found in KC via raw byte search.
- Next: build a more flexible signature (multiple word positions) and scan KC via headless script to surface embedded profiles, then look for code that walks those structures.

Deliverables: signature JSON in `out/` if needed, plus scan results with candidate addresses.

## 6) Synthesis and stop condition

**In progress**

- Cross-link AppleMatch callers (none yet), MACF hook helpers, profile-structure scans, and the new pointer-table results. Current strongest lead: 512-entry table at `__const` 0x-7fffdae120 pointing 333 times to `FUN_ffffff8000a5f0b0` (candidate op-entry dispatcher target). Also have three code sites with op_count/magic constants mapping to `FUN_ffffff8001565fc4`, `...158f618`, `...15ff7a8`.
- `FUN_ffffff8000a5f0b0` appears to be a tiny stub (8 bytes, single DATA reference). Next pivot: examine the data reference at `0x-7ffcb08ca4` and nearby functions in the table (e.g., top unique targets) to locate the real dispatcher/action walker.
- Stop when one or more functions are consistently referenced across pivots and show node-array walking with two successors and action handling.

Deliverables: summary in `ResearchReport.md` of evidence-backed dispatcher candidates and recommended next probes.
