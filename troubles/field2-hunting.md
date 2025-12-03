# Field2 hunting

## Overview

This troubleshooting note tracks the ongoing attempt to understand the third 16‑bit payload field in policy graph nodes (our `field2`), beyond the cases that clearly line up with known filter IDs. On this Sonoma host, most nodes carry low `field2` values that match the current filter vocabulary and behave like classic `filter_arg` indices into literal/regex or small enumerations. A small but important set of nodes, however, use higher values (for example 2560, 170, 174, 115, 109, 165, 166, 10752, 16660) that do not match any known filter IDs, literal indices, or obvious table offsets, and appear only in richer platform and mixed-profile graphs. The goal here is to keep a grounded record of what has been tried, what outside sources say, and what next steps are likely to be productive, so that future work does not repeat the same blind alleys.

## Local evidence so far (host baseline)

- Mixed network probes (`v4_network_socket_require_all` and `v7_file_network_combo` in `book/experiments/probe-op-structure/sb/build`) produce nodes where tag 0 has `field2=2560` tied to a flow‑divert literal; simplified profiles that isolate flow‑divert in cleaner SBPL lose this high value and collapse back to low filter IDs.
- Anchor sweeps (`probe-op-structure/out/anchor_hits.json`) show anchors mostly mapping to generic path/name `field2` shapes; the {7, 2560, 2} triple tied to flow‑divert appears only in the richer probes, suggesting a context‑dependent or composite region.
- The `bsd` platform profile (`book/examples/extract_sbs/build/profiles/bsd.sb.bin`) contains several “high” `field2` values (170, 174, 115, 109, 16660) that cluster around literals like `/dev/dtracehelper` and `posix_spawn_filtering_rules`. Targeted SBPL probes that try to reproduce just those cases only ever surface low filter IDs; the high codes remain confined to the full profile.
- In `bsd`, the tag 0 / `field2=16660` node is a widely shared tail: it has a single valid successor (node 0, tag 27, `field2=18`) and many predecessors across operations, consistent with a shared sink or default‑tail construct.
- The `airlock` profile shows high `field2` values 165, 166, and 10752, all confined to a single operation ID and not visible in simpler probes, suggesting profile‑local, platform‑specific use.
- Cross‑checking high `field2` values against known literal indices, regex indices, and other table offsets shows no direct equality; the high constants are distinct from the current vocabulary and literal table positions.

This evidence supports a picture where most of the graph uses the “public” filter vocabulary and AppleMatch‑backed tables as expected, while some regions (platform tails, mixed network constructs, posix_spawn‑related logic) rely on internal filters or flag‑augmented arguments we do not yet understand.

## Web agent advice

We’d been pushing on the “field2” problem: on this Sonoma host, most node payloads line up cleanly with known filter IDs, but a handful of high values (2560 in mixed network probes, 170/174/115/109/16660 in `bsd.sb.bin`, 165/166/10752 in `airlock`) don’t match any current vocabulary or literal/regex indices. We built probes and a census showing that 2560 only appears in richer mixed network graphs (and disappears in simplified SBPL), the bsd 16660 node is a widely shared tail reached from many ops, and airlock’s high codes are confined to one operation. The “other model” summarized this and we documented it in the `field2-filters` experiment.

You then had me formulate a single, detailed question for a web agent that could use public literature and web search. That question essentially asked: is there any published mapping or deeper explanation of this “field2” slot in modern Seatbelt blobs (especially for high values like 2560/16660), and what does the external record say about how to interpret or experiment on it? I also wrote a separate explanation of what we mean by “Field2” in this project so the web agent could align its own understanding of Seatbelt with our local model.

The web agent responded not with an immediate answer but first with its own questions to tighten the picture. It asked (1) whether, for high field2 values, a cross-profile census grouping by `(tag, op-id, field2)` shows those triples recurring across profiles/versions or whether they’re profile‑local. Based on our existing census and prior work, I could say that 16660/tag 0 in `bsd` is a shared sink reached from many ops in that single profile, airlock’s high values appear only in one op in airlock, and 2560 is tied to mixed network probes, but we don’t yet have a multi‑OS, multi‑host dataset, so beyond this host we effectively “don’t know.” It then asked (2) whether we’d checked if high field2 values correlate better with any other known table/index (literal/regex/vnode-type/etc.) rather than with filter IDs; I answered that we’d already done that: the high values do not equal literal indices or offsets, and don’t obviously match any existing vocabulary tables. Finally, it asked (3) whether the tag 0 / field2=16660 node in `bsd.sb.bin` behaves structurally like a shared sink or shows local branching; I answered that we’ve already walked that region and it behaves like a shared tail: one valid successor and many predecessors across operations.

After that exchange, the web agent gave a long, literature-backed answer. It anchored our “field2” in the classic node layout: `opcode`, `filter`, `filter_arg`, and two transitions, with `filter_arg` exactly matching our field2. It stressed that public work (Blazakis, SandBlaster, SandScout, later surveys) never published a richer bit-level layout for macOS 13/14: `filter_arg` is a 16‑bit, filter‑specific payload; tools treat it as opaque and learn meanings by differential compilation, not by decoding flags. There are no public mappings for constants like 2560 or 16660. It then laid out plausible mechanisms behind the high values: (a) AppleMatch/regex/literal caches with extra indirection or flag bits; (b) metafilter glue implemented as subgraphs that may use internal pseudo‑filters and arguments not exposed in public SBPL; (c) hidden filter kinds used only in platform/bsd/airlock profiles; and (d) possible flag bits carved out of `filter_arg` (pointing at patterns like 0x4114 = 0x4000|0x0114 and 0x0A00/0x2A00). It pointed out that our bsd tail node matches the expected shape of a shared default/special tail, where such flags would be natural. Its concrete guidance was: treat field2 as “raw filter_arg with possible flags”, derive views like low/high bits rather than renaming it to a new concept, classify metafilters and tails by graph shape instead of overfitting constants, keep “unknown high” values in a separate namespace instead of forcing them into existing vocabularies, and, ultimately, let Sandbox.kext be the arbiter by finding where the kernel masks and shifts this field. I reviewed this answer and concluded it’s consistent with our substrate and local evidence: it doesn’t give us new numeric mappings, but it confirms that we’re ahead of the public record on these Sonoma constants and that the next real progress depends on kernel-side analysis rather than more SBPL‑only experiments.

## Working hypotheses (explicit)

- `field2` is the historical `filter_arg` payload: a 16‑bit value whose semantics depend on the filter associated with the node.
- For low, well‑behaved nodes, `field2` directly encodes indices or small enumerations that line up with the current filter vocabulary and literal/regex tables.
- For “high” values seen only in platform profiles or richer probes (2560, 16660, etc.), at least one of the following is true:
  - they are arguments to internal filter kinds that are not present in the current SBPL/vocabulary map but otherwise follow the same “index/payload” model;
  - they carry additional structure inside the 16‑bit word (for example, a 0x4000‑style “special tail / platform‑only / meta‑glue” flag in the high bits, with the low bits retaining an index), even though the exact bitfield split is not yet known;
  - they mark shared tail regions or metafilter glue nodes where graph shape and position, not the literal numeric value, carry most of the semantic weight.
- Existing SBPL‑only probes have likely hit diminishing returns for these cases; the remaining structure depends on how Sandbox.kext consumes `filter_arg` at evaluation time.

These hypotheses should remain tagged as provisional (`status: partial` at best) until we have kernel‑side evidence.

## Good next steps (short horizon)

- **Stabilize the data model**
  - In graph decoders and capability catalogs, represent this slot explicitly as:
    - `field2_raw: u16`
    - `field2_hi:  u16 = field2_raw & 0xC000`
    - `field2_lo:  u16 = field2_raw & 0x3FFF`
  - Name the stored value in the decoded node type as `filter_arg_raw = field2_raw` to stay aligned with the published node layout, and treat `field2_hi` / `field2_lo` as derived views used only for analysis.
  - Use `field2_lo` as a candidate payload only when it clearly matches known filter IDs or other small, well‑behaved values; for “high” or unclear cases (2560, 166, 10752, 16660, etc.), carry them as an `UnknownFilterArg(field2_raw)` rather than coercing them into the low‑ID vocabulary.

- **Systematic census on this host**
  - Regenerate a host‑wide census of `(profile, op-id, tag, field2)` for all compiled profiles we already decode (platform, airlock, app sandbox examples).
  - For high values, record their structural context: whether they are terminal, shared tails (fan‑in), or internal glue (fan‑out/fan‑in), and track `(tag, field2_hi, field2_lo)` distributions in a side channel.
  - Check whether using `field2_lo` in place of `field2_raw` aligns these nodes with known low‑ID payloads, without assuming any particular interpretation of the high bits.

- **Graph‑shape classification**
  - Keep classification of graph structure (require‑all/any/not, shared tails, default‑op tails, and similar motifs) driven primarily by node shape and position in the graph, with `field2_*` values treated as auxiliary evidence rather than primary keys.
  - For nodes classified as “shared tails” or “metafilter glue,” record their `(tag, field2_hi, field2_lo)` distributions for later comparison, but avoid baking any semantic claims about specific constants into the core model until there is clear Sandbox.kext evidence for the bitfields behind them.
  - Identify common graph motifs where high `field2` values appear (shared tails, metafilter regions, posix_spawn‑related subgraphs, flow‑divert clusters) and record how often each motif recurs on this host.

- **Kernel‑side reconnaissance (when Ghidra work resumes)**
  - Locate the core evaluator in `Sandbox.kext` that walks nodes and reads `filter_arg`.
  - Instrument or statically analyze how it masks and shifts the `filter_arg` field (look for `& 0x3FFF`, `& 0x4000`, `>> 8`, etc.).
  - Use those masks as the authoritative definition of any bitfields inside `field2`, then re‑interpret existing high constants under that scheme.

- **Guardrails for interpretation**
  - Avoid promoting any specific numeric mapping (for example “2560 == flow‑divert filter X” or “16660 == bsd default tail Y”) without kernel evidence.
  - Keep experiment notes and capability catalogs explicit about where conclusions rest on SBPL‑only structure vs. confirmed runtime behavior.

Taken together, this should keep the `field2` work anchored in static artifacts and the public Canon while making it straightforward to plug in kernel‑sourced bitfield knowledge once the disassembly work catches up.
