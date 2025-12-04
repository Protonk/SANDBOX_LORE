

## Chat agent readout

### Framing and roles

The thread started with the user asking whether the web agent understood a project-local notion of “field2.” The web agent answered that it did not and asked for a restatement in local terms. The user provided a compact definition:

* In decoded policy graphs, each node record has two edge pointers and a third 16-bit “payload” field, called `field2`.
* For many nodes, `field2` matches known filter IDs from the harvested vocabulary (path, mount-relative-path, global/local-name, socket-type, etc.) and lines up with system profiles.
* Some nodes carry higher `field2` values that do not map to this vocabulary and only appear in richer graphs: flow-divert probes (~2560), bsd tail (~170/174/115/109/16660), airlock (~165/166/10752).

The user explicitly instructed the web agent to ask one or two questions that a local codex agent could answer. From that point on, most of the thread was message passing between:

* a web agent with internet access and Seatbelt background, and
* a codex agent operating on the actual repo, decoded graphs, and Ghidra/KC, following the web agent’s instructions and reporting back.

The human user helped set up the pattern, then largely stayed out of the way.

---

### Initial model of `field2`

With the local definition in hand, the web agent:

* Mapped `field2` to the canonical `filter_arg` field from Blazakis/SandBlaster/etc. (third 16-bit slot in a node after kind/opcode and filter id).
* Checked public sources for Sonoma-era format changes and explicit mappings of high argument values like 0x0a00 or 0x4114.

The conclusion from public material:

* The only documented meaning remains “filter-specific payload / argument,” not a separate “third field” with a new role.
* There is no published Sonoma-era mapping from specific high payload values to concrete filters or branch types.
* It is compatible with public descriptions that:

  * internal filters exist beyond the public SBPL vocabulary, and
  * `filter_arg` could encode flags in high bits with indices in low bits, but these details are not documented.

Given the local observations (high values only in rich profiles, bsd tail behaving like a shared sink, 0x4114/0x0a00/0x2a00 patterns), the web agent suggested:

* Treat `field2` as `filter_arg_raw` and derive `hi/lo` views (e.g., `raw & 0xC000`, `raw & 0x3FFF`).
* Let graph shape and role (shared tail, metafilter glue, etc.) drive classification rather than overfitting the numeric codes.
* Use kernel-side evidence (Sandbox.kext) to see how that payload field is masked, shifted, or bit-tested at evaluation time.

---

### Headless Ghidra enablement

To get kernel-side evidence, the codex agent needed headless Ghidra runs inside a sandboxed environment. Initial attempts to run `analyzeHeadless` on the BootKernelCollection hit a JDK selection prompt and `java_home.save` EPERM issues.

The web agent:

* Explained how Ghidra chooses its settings directory and JDK cache (defaulting under `$HOME/Library/...`).
* Recommended redirecting the settings directory to a repo-local path using VM properties (`application.settingsdir`, `user.home`) and seeding `java_home.save` there with the JDK path.
* Advised dropping unsupported flags (`-vmPath`, `-logFile`) and relying on `JAVA_TOOL_OPTIONS` plus repo-local `HOME` / `GHIDRA_USER_HOME` to keep everything writable under the project.

The codex agent implemented this wiring. After that, headless Ghidra runs were stable and could execute custom scripts against an existing project without interactive prompts.

---

### First kernel-side probes

With headless working, the codex agent:

* Located generic blob readers like `__read16` and dumped their callers.
* Observed that callers (`__readaddr`, `__readstr`, syscall mask helpers, state flag iterators, `_match_network`, etc.) applied generic `& 0xffff` masking for bounds or range checks.
* Found no comparisons or bit tests against the specific high `field2` constants (0x0a00, 0x4114, 0x2a00, etc.).

The web agent classified these as deserializers and generic table readers—useful for confirming “this field is 16-bit” but not for interpreting the semantics of `field2`. The next step was to find the actual policy evaluator.

The codex agent then:

* Identified the main evaluation function (`_eval`) in the sandbox kext.
* Confirmed that `_eval`:

  * fetches a tag byte from `[profile_base + cursor]`,
  * performs bounds checks on the cursor against profile limits, and
  * dispatches via a tag-based jump table.
* Saw that one tag arm treated a 24-bit payload via a helper, with masks like 0xffffff and 0x7fffff, but still without any masks/compares tied to the unknown `field2` values.

This established `_eval` as a bytecode/VM front-end over a “profile stream,” not yet a clear view of fixed-stride node records.

---

### Systematic layout and struct search

From there, the web agent shifted the goal from “spot the node layout manually” to “build scripted searches for array-of-struct patterns under `_eval` and in the sandbox kext more broadly”:

* The codex agent wrote a series of headless scripts:

  * A node layout probe to identify a base pointer, index register, stride, and loads off that base.
  * An eval-callee walker to probe helpers reachable from `_eval`.
  * A global struct scan for functions that use “base + scaled index” to access a small fixed-size struct with at least one byte and multiple halfword loads.

The probes confirmed:

* `_eval` itself behaves like an interpreter over a byte stream:

  * tag at `[base + cursor]`,
  * a follow-up byte at the next position,
  * no obvious cluster of “tag, filter, edge0, edge1, payload” loads from a fixed stride array.
* One helper showed a small “halfword + byte” pattern and appears to be a tag-specific operand decoder (24-bit immediate), not a full node struct.
* Another helper showed multiple halfword loads and a word load, but without a clear linkage to sandbox graph semantics.

The global scan, restricted to functions reachable from `_eval` and tuned for “[byte + ≥2×u16] from a base + scaled index,” reported that:

* No function under `_eval` cleanly matched the classic Blazakis node struct shape at the level of “one struct, one stride with byte + two halfword fields at small offsets.”
* Only a couple of weak candidates appeared, with large offsets or unclear context, and no usage hints that tied them convincingly to sandbox policy nodes.

The codex agent summarized this as: under the current heuristics, the kext does not expose a simple, directly indexed `[tag, filter, edge0, edge1, field2]` array reachable from `_eval`.

---

### Interpreting the negative result

The web agent then connected this back to the canonical literature and to the original `field2` question:

* Classical write-ups describe the logical node layout (kind, filter, filter_arg, two transitions) and a compiler that emits such nodes into a blob.
* Modern descriptions still treat the kernel evaluator as a central `eval` over a policy, but do not publish a Sonoma-era struct layout.
* The lack of a clean `[byte + 2×u16]` pattern under `_eval` in 14.4.1, despite systematic scanning, is consistent with the kernel now running a bytecode VM over a more compact or refactored representation rather than over a simple fixed-stride node array mirroring the decoded `.sb.bin` shape.

In other words:

* The decoded `.sb.bin` graphs the project works with still present nodes as `[tag, filter, edge0, edge1, field2]`.
* The kernel’s internal runtime representation has evolved enough that there is no straightforward, static “node struct” one can rediscover by generic struct-pattern scans in the KC, at least not under `_eval`.

For the `field2` experiment, this means:

* Kernel-side pattern matching for “[byte, byte, u16, u16, u16]” is effectively exhausted on this host; further widening of the same heuristic is unlikely to produce a clear mapping.
* Progress on the semantics of high `field2` values should instead focus on:

  * tracking how argument-like values derived from the profile stream are masked, bit-tested, or used as indices in `eval` and its helpers, and
  * examining userland `libsandbox` compilation/parsing paths, where the logical node layout is closer to the project’s decoded graphs.

---

### Outcome relative to `field2`

The thread ends with a clarified picture:

* `field2` in the decoded graphs remains aligned with the canonical `filter_arg` concept: a per-node payload whose meaning is filter-specific.
* High `field2` values seen only in rich profiles and tails are not mapped in public sources and do not appear as obvious constants or struct fields in kernel static analysis under the VM front-end.
* The project now has a set of headless Ghidra tools and negative results showing that the older “find the node array via fixed-stride struct patterns under the evaluator” method does not directly carry over to Sonoma’s Sandbox.kext.
* Future work on `field2` mapping is steered toward usage-level analysis (bit ops, index patterns) and userland compiler behaviour rather than expecting a simple kernel-side struct layout to fall out of static pattern scans.


---

# Field2 hunting (closed)

This note captures the hunt for the third 16‑bit payload slot in compiled PolicyGraph nodes on this Sonoma host. Early drafts called it `field2`; the decoder now exposes it as `filter_arg_raw` (with `field2_hi = raw & 0xc000`, `field2_lo = raw & 0x3fff`). The search is **closed**: low values line up with the public filter vocabulary, every remaining unknown is bounded by tag/op context, and the kernel reads this slot as a raw u16 with no hi/lo split or obvious node struct.

Key artifacts (all under `book/experiments/field2-filters/`):
- Inventories: `out/field2_inventory.json`, `out/unknown_nodes.json`.
- System + probe SBPL: `sb/` and `sb/build/*.sb.bin` (including `bsd_ops_default_file`, `airlock_system_fcntl`, flow-divert variants).
- Ghidra evaluator/helper dumps: `dumps/ghidra/out/14.4.1-23E224/find-field2-evaluator/` (`field2_evaluator.json`, `helper.txt`, `eval.txt`, `candidates.json`).
- Ghidra struct hunt (negative): `dumps/ghidra/out/14.4.1-23E224/find-field2-evaluator/node_struct_scan.txt` and `.json` (0 real candidates reachable from `_eval`).
- Scripts: `harvest_field2.py`, `unknown_focus.py`, `book/api/ghidra/scripts/find_field2_evaluator.py`, `kernel_node_struct_scan.py`.

## What is known

### Profile-side facts (decoded graphs)
- `bsd`: highs {16660 on tag 0, ops 0–27, hi=0x4000; 170/174/115/109 on tag 26, op-empty}. Lows match vocab (path/socket/iokit/right-name/preference-domain/mac-policy-name).
- `airlock`: highs {165, 166, 10752} on tags 166/1/0 tied to op 162 (`system-fcntl`); synthetic `airlock_system_fcntl` adds sentinel 0xffff (hi=0xc000) on tag 1. Lows otherwise path/socket.
- `sample`: single sentinel 3584 (hi=0, lo=0xe00) on tag 0; rest low IDs (path/local/remote).
- Flow-divert mixed probes (`v4_network_socket_require_all`, `v7_file_network_combo`, `net_require_all_domain_type_proto`): include a node with `filter_arg_raw = 2560` (hi=0, lo=0x0a00) tied to literal `com.apple.flow-divert`, fan_in=0, fan_out=2→0, op-empty; only appears when domain+type+protocol are all required. Simplified network-only variants collapse to low IDs.
- Other synthetic probes (dtracehelper/posix_spawn, bsd_tail_context, flow_divert_variant, flow_divert_mixed) collapse to low IDs; no reproduction of bsd highs outside the canonical `bsd` blob.

### Kernel-side facts (arm64e sandbox kext)
- `_eval @ fffffe000b40d698` is a bytecode VM over the profile blob; masks 0x7f/0xffffff/0x7fffff for other operands but **no** 0x3fff/0x4000 masks on the u16 payload.
- `__read16 @ fffffe000b40fa1c` is the u16 reader: bounds-check + `ldrh`, no masking or bit tests. Payload is forwarded raw.
- No immediates or masks for the unknown constants (16660/2560/10752/0xffff/3584) appear in evaluator/helper dumps.
- Struct hunt: `kernel_node_struct_scan.py scan ...` over all functions reachable from `_eval` finds **no** fixed-stride `[byte + ≥2×u16]` node layout; only two noisy non-sandbox hits. This effectively rules out a Blazakis-style in-kernel node array on 14.4.1.

**Bottom line:** `filter_arg_raw` is consumed as a plain u16; hi/lo splitting is an analytic convenience only. The unmapped values remain: 16660, 2560, 10752, 165, 166, 170, 174, 115, 109, 3584, 0xffff.

## How we got here (paths and outcomes)

1) **Census and tagging:** `harvest_field2.py` + `unknown_focus.py` over system profiles and probes to locate all unknowns with tag/op/fan-in/fan-out context (`out/field2_inventory.json`, `out/unknown_nodes.json`).
2) **SBPL probes:** single-filter and mixed profiles to peel highs into simpler graphs. Result: either collapse to low IDs or one new sentinel (0xffff) without mapping the original highs.
3) **Kernel helper/evaluator:** carved `com.apple.security.sandbox`, located `_eval` and `__read16`, confirmed raw-u16 handling, ran mask/imm searches for 0x3fff/0x4000/0xc000 and the unknown constants with negative results.
4) **Struct search:** `kernel_node_struct_scan.py` over `_eval`’s callees and callgraph reach produced 0 viable `[byte + 2×u16]` structs. Treat this as definitive: the evaluator is VM-style, not a fixed node array.

## Status and closure

Closed. Unknowns are bounded by structure (tags, ops, fan-in/out) but unmapped. No kernel-side hi/lo split or recoverable node struct was found. Further progress would require new work (e.g., helper-level compare/index analysis or userland `libsandbox` compiler study) and should be tracked as a new trouble or experiment, referencing these artifacts for context.

## If reopened later

- Re-use existing artifacts as ground truth (inventories, unknown_nodes, evaluator/helper dumps, struct-scan negative).  
- Focus any new work on where the raw u16 is *used* (equality tests or table indices), not on recovering a fixed node layout.  
- Keep this note immutable; log new work in a fresh note and link back here.
