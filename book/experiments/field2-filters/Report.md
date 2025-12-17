#+#+#+#+#+#+#+#+━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Field2 ↔ Filter Mapping — Research Report

Status: complete (negative)

## Purpose and closure posture

This experiment set out to understand the third u16 slot carried by compiled PolicyGraph nodes on this host baseline. Historically this slot was discussed as “field2”; in this repo it is now named structurally as `filter_arg_raw`. The goal was to connect that u16 to the host Filter vocabulary where appropriate, and to determine whether the remaining high/out-of-vocab values have interpretable semantics (for example, a flag split or a stable auxiliary identifier).

The experiment is closed as a negative result. On this host (`world_id sonoma-14.4.1-23E224-arm64-dyld-2c0602c5`), we have exhausted (1) SBPL-based synthesis and perturbation, and (2) kernel-side structure hunting in the sandbox evaluator path, without finding evidence for a kernel-side hi/lo split, a fixed-stride node array, or stable semantic interpretation of the remaining high/out-of-vocab u16 values. The u16 is read and propagated as a raw u16 by the evaluator’s reader helpers. The only evidence-backed interpretation boundary we keep is structural: the u16 slot exists (or not) depending on tag layout; and when the tag’s u16 role is “filter vocabulary id”, the value may or may not resolve in the host filter vocabulary.

This closure is not “we learned nothing.” We learned a stable set of structural relationships and constraints on this host, and we updated the repo’s IR to preserve those relationships deterministically.

## World, inputs, and evidence model

All claims in this report are about the single frozen world `sonoma-14.4.1-23E224-arm64-dyld-2c0602c5`. The primary evidence is compiled profiles and host-bound mappings.

Canonical vocabulary mappings live at `book/graph/mappings/vocab/filters.json` and `book/graph/mappings/vocab/ops.json` (status: ok). Canonical profiles used throughout this work are `book/examples/extract_sbs/build/profiles/airlock.sb.bin`, `book/examples/extract_sbs/build/profiles/bsd.sb.bin`, and `book/examples/sb/build/sample.sb.bin`. Experimental probes (SBPL sources and compiled blobs) live under `book/experiments/field2-filters/sb/` and `book/experiments/field2-filters/sb/build/`.

The experiment’s primary outputs are `book/experiments/field2-filters/out/field2_inventory.json` (per-profile histograms, tag counts, and hi/lo census) and `book/experiments/field2-filters/out/unknown_nodes.json` (concrete unknown/high nodes with fields, fan-in/out derived from the current edge assumptions, and op reach when available).

Kernel-side evidence is sourced from Ghidra analysis outputs under `dumps/ghidra/out/14.4.1-23E224/find-field2-evaluator/`, driven by scripts under `book/api/ghidra/scripts/`.

## Approach (what we did)

We approached “field2” as a structural slot whose meaning must be inferred from repeated host witnesses. The work progressed in four strands that fed one another.

First, we established and reused a tag-aware structural decoder and tag layout map. The repo’s tag layout mapping for this world is `book/graph/mappings/tag_layouts/tag_layouts.json` (derived in the sibling experiment `book/experiments/tag-layout-decode`). This mapping asserts a record size (12 bytes for the tags in scope), identifies edge field indices, and identifies which field indices are payload fields (including the u16 slot used as `filter_arg_raw` for payload-bearing tags). This made it possible to speak precisely about “the u16 slot” without relying on ad hoc record parsing.

Second, we harvested inventories over canonical blobs and probe blobs. The scripts `book/experiments/field2-filters/harvest_field2.py` and `book/experiments/field2-filters/unknown_focus.py` aggregate, for each profile, the multiset of observed `filter_arg_raw` u16 values, their tag distributions, and (where decode makes it possible) their attachment to literals/anchors and to op reach. The inventory is intentionally descriptive: it records which values appear, where they appear (tag context), and how often; it does not attempt to assign semantics.

Third, we ran a set of SBPL probe families designed to surface and isolate the out-of-vocab/high u16 values seen in system profiles. The probe families include “flow-divert require-all” variants, system-fcntl variants, and attempts to reproduce bsd-tail highs in smaller contexts. A repeating pattern emerged: many simplified probes collapse to a generic low-ID scaffolding and do not reproduce the system-only highs; conversely, richer mixed probes sometimes preserve a specific unknown (notably the flow-divert 2560 value) under a stable predicate combination.

Fourth, we hunted for kernel-side structure and transforms. Using the extracted arm64e sandbox kext (`/tmp/sandbox_arm64e/com.apple.security.sandbox`) and headless Ghidra tooling, we identified u16 reader helpers (`__read16`) and inspected the evaluator (`_eval`) and its reachable neighborhood for (a) bit masking/splitting of the u16 (e.g., `0x3fff`, `0x4000`) and (b) evidence of a fixed-stride node array structure. The reader helper loads a u16 and stores it without masking; `_eval` contains other masks (e.g., `0x7f`, `0xffffff`, `0x7fffff`) but not the hypothesized hi/lo masks for `filter_arg_raw`. A dedicated “node struct scan” over all functions reachable from `_eval` found no fixed-stride `[byte + ≥2×u16]` node layout. This supports the “bytecode VM over a profile blob” model for this host rather than a directly indexed node array model.

## Results (what we learned)

### Low values align with the host filter vocabulary

Across the canonical `bsd` and `sample` profiles, low u16 values in the payload slot correspond directly to filter IDs in `book/graph/mappings/vocab/filters.json`. The inventory includes repeated witnesses for common filter IDs such as path/name/socket classes and system-specific filters (`right-name`, `preference-domain`, iokit-related filters, and others). This is the positive core: when a tag’s payload u16 is used as a filter vocabulary id, the mapping is stable and matches the host vocabulary.

### A bounded set of out-of-vocab/high values persists

The canonical profiles and probe corpus produce a bounded set of out-of-vocab/high values, clustered by tag context and by profile context. The salient clusters are:

`flow-divert` cluster: `filter_arg_raw=2560` (`0x0a00`) appears in mixed “require-all domain+type+protocol” socket probes tied to the literal `com.apple.flow-divert`. The signal is stable across TCP and UDP variants and disappears when the profile is simplified to any pair of those predicates. The observed nodes are tag 0, op reach is empty, and the node’s fan-out is consistent with the “edges to node 0” structure captured in `book/experiments/field2-filters/out/unknown_nodes.json`.

`bsd` tail cluster: `filter_arg_raw=16660` (`0x4114`) appears on a tag 0 node in the full `bsd` profile and is reachable from a broad op slice (ops 0–27 in the current op reach encoding). This is the only unknown/high value with broad op reach on this host. Additional bsd highs (`170`, `174`, `115`, `109`) appear on tag 26 nodes and are op-empty in the current census.

`airlock` system-fcntl cluster: `filter_arg_raw=165`, `166`, and `10752` (`0x2a00`) appear in the `airlock` profile on tags 166/1/0 with op reach concentrated on the `system-fcntl` op. A probe (`airlock_system_fcntl`) also surfaces a sentinel-like value `0xffff` in tag 1, with hi bits set (`0xc000`) in the hi/lo census.

`sample` sentinel: `filter_arg_raw=3584` (`0x0e00`) appears on a tag 0 node, op-empty, and recurs in probe-like contexts that resemble the sample’s structure.

The experiment treats these values as “structurally bounded but semantically opaque” for this world. We keep their contexts and counts; we do not assert a kernel-consumed semantic split.

### Kernel-side structure hunt is negative for u16 splitting and for a fixed node array

The kernel-side work in `dumps/ghidra/out/14.4.1-23E224/find-field2-evaluator/` supports two negative conclusions.

First, the u16 reader helper (`__read16`) loads and forwards the u16 without applying masks or bitfield extracts. Second, neither `_eval` nor its reachable neighborhood contains the hypothesized `0x3fff`/`0x4000` masks that would indicate a stable hi/lo split of `filter_arg_raw`. This does not prove that no semantics exist, but it eliminates a broad and previously plausible hypothesis space.

Separately, a dedicated scan (`kernel_node_struct_scan.py`) over all functions reachable from `_eval` found no fixed-stride node array layout of the form “byte tag plus u16 fields at constant offsets.” The evaluator behaves like a bytecode VM over a profile blob on this host rather than walking a directly indexed node array. This constrains how future semantics work would need to proceed (table lookups and derived indices rather than a simple struct).

## How the repo now preserves the result (structural contract)

This experiment produced two repository-level contract improvements that reduce ambiguity for future work without prematurely enforcing cross-world assumptions.

First, u16 role is now explicit per tag for this world. The mapping `book/graph/mappings/tag_layouts/tag_u16_roles.json` declares, for each tag in scope, whether the payload u16 slot is intended to be treated as a filter vocabulary id (`filter_vocab_id`), an opaque argument u16 (`arg_u16`, with tag10 as the exemplar), or absent/meta-only (`none/meta`). This avoids reintroducing implicit assumptions such as “payload u16 always means filter id” across all tags.

Second, the decoder now exposes structure with provenance rather than silently guessing. `book/api/decoder/__init__.py` remains permissive, but it now attaches `filter_arg_raw`, `u16_role`, and (when applicable) `filter_vocab_ref` / `filter_out_of_vocab` directly on decoded nodes, and it records provenance for layout selection and literal reference recovery. The decoder does not enforce “unknown-but-bounded”; discovery stays possible.

To protect the learned tag/layout/role relationships on this host without freezing a closed unknown inventory, we added a lightweight validation job and guardrail test. The validation job `structure:tag_roles` lives in `book/graph/concepts/validation/tag_role_layout_job.py` and is registered via `book/graph/concepts/validation/registry.py`. It runs on the pinned canonical corpus and verifies the two structural invariants: observed tags have declared roles, and tags whose roles imply a payload slot have layouts. It also reports vocab hit/miss counts and fallback usage, but it does not fail merely because values are out-of-vocab.

The guardrail test `book/tests/test_field2_unknowns.py` continues to pin a known set of unknown/high values observed by this experiment’s inventory; it is intentionally conservative and can be adjusted deliberately when warranted. Flow-divert payload 2560 has been reclassified as “characterized, triple-only” (tag0, `u16_role=filter_vocab_id`, literal `com.apple.flow-divert`), so it is no longer part of the unknown set; the guardrail now asserts that only triple flow-divert specs emit 2560 and that non-triples do not.

## Non-claims and limitations

This report does not claim a semantic interpretation of out-of-vocab/high values such as 2560, 16660, 10752, 0xffff, or 3584. It does not claim that these values are sentinels, indices, or flags; it claims only that they are observed, context-bounded u16 payloads in compiled profiles on this host.

This report also does not claim that the tag layout map is globally complete. `book/graph/mappings/tag_layouts/tag_layouts.json` is “best-effort” and was derived primarily from literal/regex-bearing tag behavior in canonical blobs; tags outside that scope may require additional decoding work.

Finally, platform/runtime gates (e.g., inability to apply certain system profiles) mean that this experiment is predominantly static. Runtime semantics, if they exist, are not established here.
