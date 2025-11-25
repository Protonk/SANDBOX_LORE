# macOS Sandbox Concept Atlas

This document extracts and organizes the core concepts of the macOS Seatbelt sandboxing model, strictly based on the following files: `Orientation.md`, `Concepts.md`, `Appendix.md`, `ERRATA.md`, `Reading.md`, and `Canon.md`. It maps each concept’s definition, use, and divergence across the substrate, and proposes concrete edits to improve clarity and coverage.

---

## 1. Overview

Apple’s macOS sandboxing framework (Seatbelt) confines processes to a predefined set of permitted operations, as specified in a profile. This corpus captures a highly intentional and internal-facing model of how Seatbelt’s policy system works, including its high-level structure (from human-readable source to kernel-enforced decision graph), vocabulary, and tooling interface. The documentation centers around a vocabulary of concepts (in `Concepts.md`), a lifecycle model (in `Orientation.md`), a detailed syntax and format reference (in `Appendix.md`), and a set of recorded divergences from observed macOS behavior (in `ERRATA.md`). The result is a tight, expressive model capable of supporting analysis and tooling (e.g. decompilers, visualizers, reconcilers).

This report inventories the explicitly defined or operationally relied-on core concepts, traces where they live in the corpus, and highlights invariants, overlaps, frictions, and drift. The overall documentation is strong and internally consistent, with a few minor gaps and normalization needs—especially in surfacing parameterization, harmonizing naming of internal structures, and accounting for version-sensitive behaviors in macOS 14.

---

## 2. Concept-by-Concept Atlas

Each concept below includes:

- **Definition**: Synthesized from all defining language in the corpus.
- **Where it lives**: Files and sections where it is introduced, used, or qualified.
- **Invariants**: Stable properties that hold across files.
- **Version Caveats**: Noted deviations in behavior or form under macOS 14.x (from `ERRATA.md`).

### SBPL Profile

- **Definition**: The human-authored, Scheme-like source form of a sandbox policy. Declares version, default rule, and operation-specific rules with filters and modifiers.
- **Where it lives**:
  - `Concepts.md`: Introduced, core definition.
  - `Orientation.md`: Stage 1, writing.
  - `Appendix.md`: DSL syntax and example cheatsheet.
- **Invariants**: Always begins with `(version ...)` and `(deny default)`. Operations are symbolic.
- **Version Caveats**: Some profiles now use parameterization via `(param ...)`, not described in core text—see ERRATA.

### Operation

- **Definition**: A symbolic name for a category of kernel action subject to sandbox mediation (e.g. `file-read*`, `mach-lookup`).
- **Where it lives**:
  - `Concepts.md`: Defined.
  - `Orientation.md`: Used extensively, especially in Stage 4.
  - `Appendix.md`: Categorized and enumerated in filter/operation lists.
- **Invariants**: Operations map to integer IDs in the compiled binary; each has a unique decision graph root.
- **Version Caveats**: Discovery via public headers/symbols is restricted in macOS 14.

### Filter

- **Definition**: A key–value predicate narrowing the applicability of a rule (e.g. path, entitlement, vnode-type).
- **Where it lives**:
  - `Concepts.md`: Defined with examples.
  - `Orientation.md`: Described conceptually.
  - `Appendix.md`: Filter key reference and syntax.
- **Invariants**: Appears as second-level clauses in SBPL; compiled as filter nodes with match/unmatch edges.
- **Version Caveats**: None directly, though regex decoding requires workaround tooling.

### Metafilter

- **Definition**: Logical combinators in SBPL for joining filters: `require-all`, `require-any`, `require-not`.
- **Where it lives**:
  - `Concepts.md`: Defined and described.
  - `Orientation.md`: Listed among four key constructs.
  - `Appendix.md`: Shown in SBPL syntax examples.
- **Invariants**: Always compiled structurally (not as named graph nodes); syntax matches logical expectations.
- **Version Caveats**: None.

### Decision

- **Definition**: The terminal outcome (allow or deny), possibly annotated with action modifiers like `with report` or `with user-consent`.
- **Where it lives**:
  - `Concepts.md`: Formal description.
  - `Orientation.md`: Described in runtime enforcement.
  - `Appendix.md`: Terminal node opcodes and modifiers.
- **Invariants**: Every operation evaluation ends in a decision; modifiers do not affect allow/deny logic.
- **Version Caveats**: Some newer modifiers (e.g. user consent) more prevalent but behavior unchanged.

### Action Modifier

- **Definition**: SBPL annotations that attach side-effects to decisions, like logging or requiring user approval.
- **Where it lives**:
  - `Concepts.md`: Defined.
  - `Appendix.md`: Examples (`with report`, `with user-consent`).
- **Invariants**: Do not change basic allow/deny; appear as wrappers or modifiers.
- **Version Caveats**: More modifiers now present in system profiles.

### Profile Layer

- **Definition**: The level at which a profile applies—platform-wide or per-process.
- **Where it lives**:
  - `Concepts.md`: Core definition.
  - `Orientation.md`: Described in core model and Stage 4.
  - `Appendix.md`: Described in policy stacking behavior.
- **Invariants**: Platform policy always evaluated before per-process.
- **Version Caveats**: Applying per-process profiles via `sandbox_apply` restricted under SIP.

### Sandbox Extension

- **Definition**: Token-based dynamic capabilities that grant access to specific resources when the token is present.
- **Where it lives**:
  - `Concepts.md`: Defined and contextualized.
  - `Appendix.md`: Filter key `extension` documented.
- **Invariants**: Allows granting access beyond static profile; used by TCC and other services.
- **Version Caveats**: None noted.

### Policy Lifecycle Stage

- **Definition**: The four conceptual stages: SBPL → compiled profile → installed profile → runtime enforcement.
- **Where it lives**:
  - `Concepts.md`: Named and defined.
  - `Orientation.md`: Dedicated section with diagrams.
  - `Appendix.md`: Sections correspond to stages.
- **Invariants**: Linear flow; tools and APIs map to specific stages.
- **Version Caveats**: Stage 3 and 4 behavior restricted in macOS 14 (e.g. `sandbox-exec` and `sandbox_apply` blocked).

### Binary Profile Header

- **Definition**: Top-level binary structure identifying format version and offsets to substructures.
- **Where it lives**:
  - `Concepts.md`: Defines structure.
  - `Orientation.md`: Discusses header fields.
  - `Appendix.md`: Enumerates format-specific header layouts.
- **Invariants**: All compiled profiles begin with such a header.
- **Version Caveats**: Some compiled profiles now report `re_table_offset = 0`, requiring format handling updates.

### Operation Pointer Table

- **Definition**: Array mapping operation IDs to root nodes in the policy graph.
- **Where it lives**:
  - `Concepts.md`: Described explicitly.
  - `Orientation.md`: Mentioned under compilation and decoding.
  - `Appendix.md`: Named "Operation Node Pointers".
- **Invariants**: Present in all formats; provides graph entrypoints.
- **Version Caveats**: None directly, but naming varies.

### Policy Node

- **Definition**: The atomic unit of the compiled profile: either a filter test or a decision node.
- **Where it lives**:
  - `Concepts.md`: Defines structure and behavior.
  - `Orientation.md`: Graph traversal discussed.
  - `Appendix.md`: Node format documented.
- **Invariants**: Each node is either a filter (with match/unmatch) or terminal decision.
- **Version Caveats**: None.

### Policy Graph

- **Definition**: The full directed graph of policy nodes per profile.
- **Where it lives**:
  - `Concepts.md`: Defined.
  - `Orientation.md`: Implicit in all compiled format discussion.
  - `Appendix.md`: Format structure and node linking described.
- **Invariants**: Each operation's rules form a subgraph; all compiled profiles represent such a graph.
- **Version Caveats**: None.

### Regex / Literal Table

- **Definition**: Shared memory table of strings and regex bytecode, indexed by filters.
- **Where it lives**:
  - `Concepts.md`: Described.
  - `Orientation.md`: Compilation notes on regex.
  - `Appendix.md`: Regex tables and pointers documented.
- **Invariants**: Used for compact representation of path and pattern filters.
- **Version Caveats**: `libMatch` not available on macOS 14; tools must decode manually.

### Profile Format Variant

- **Definition**: The on-disk binary format used—e.g., decision tree (old), graph-based (modern), or bundle.
- **Where it lives**:
  - `Concepts.md`: Overview of formats.
  - `Orientation.md`: Stages and code-mapping notes.
  - `Appendix.md`: Format-specific sections.
- **Invariants**: All variants include ops, filters, decisions; layout differs.
- **Version Caveats**: macOS 14 introduces new quirks (e.g., `re_table_offset = 0`), implying a new variant.

### Operation Vocabulary Map

- **Definition**: Mapping between numeric op IDs in the compiled blob and SBPL names.
- **Where it lives**:
  - `Concepts.md`: Describes use and importance.
  - `Orientation.md`: Advises on use in decoding.
  - `Appendix.md`: Operation name reference.
- **Invariants**: Required for decompilation and comparison.
- **Version Caveats**: Automatic discovery of op names blocked by missing symbols in sandbox kext on macOS 14.

### Filter Vocabulary Map

- **Definition**: Mapping of filter key IDs and value enums to human-readable filter expressions.
- **Where it lives**:
  - `Concepts.md`: Described.
  - `Orientation.md`: Tool guidance and mapping.
  - `Appendix.md`: Filter key reference.
- **Invariants**: Needed to reconstruct SBPL from binary.
- **Version Caveats**: None.

### Policy Stack Evaluation Order

- **Definition**: The evaluation sequence: platform policy → per-process → other MACs; result is logical AND.
- **Where it lives**:
  - `Concepts.md`: Explicit.
  - `Orientation.md`: Described in Stage 4.
  - `Appendix.md`: Policy stacking logic.
- **Invariants**: Platform deny short-circuits evaluation.
- **Version Caveats**: None.

### Compiled Profile Source

- **Definition**: The origin of a compiled profile—system profile, app sandbox template, custom SBPL.
- **Where it lives**:
  - `Concepts.md`: Defined and illustrated.
  - `Orientation.md`: Alluded to via code-mapping examples.
  - `Appendix.md`: Describes historical and current profile storage.
- **Invariants**: Source affects interpretation.
- **Version Caveats**: On macOS 14+, profiles reside as readable files in `/System/Library/Sandbox/Profiles`.

---

## 3. Frictions and Gaps

- **Parameterization** is missing from the main model and deserves formal surfacing.
- **Terminology overlap**: e.g. “Operation Node Pointers” (Appendix) vs. “Operation Pointer Table” (Concepts) could confuse readers.
- **Term drift**: “Policy Node” vs. “Operation Node” vs. “Handler” should be reconciled or annotated.
- **“Policy” vs “Profile”** distinction is not explicitly defined.
- **Platform stacking model** appears in both *Profile Layer* and *Policy Stack Evaluation* without cross-reference.
- **Regex decoding expectations** (via AppleMatch) are outdated; tooling must handle lack of library.
- **Changes in `sandbox_apply` and `sandbox-exec` behavior** under SIP are not flagged in Orientation.
- **`ERRATA.md` contains central knowledge** that should be surfaced in the main documents where possible.

---

## 4. Suggested Edits/Backlog

You are an agent tasked with updating artifacts in `guidance/`, make the following changes to `Concepts.md`, `Orientation.md`, and `Appendix.md`:

### Concepts.md
1. Add a new glossary entry for **Parameterization** that defines it as the use of `(param ...)` forms in SBPL to allow templating of profiles, requiring external input at compile time. Mention `string-append`, use in system profiles, and compile-time substitution requirements.
2. At the end of the *Profile Layer* entry, add a cross-reference: “(See also **Policy Stack Evaluation Order** for how multiple layers are applied at runtime.)”
3. At the end of the *Policy Stack Evaluation Order* entry, add: “(See **Profile Layer** for the definition of platform vs. per-process layers.)”
4. In the *Policy Node* entry, append: “Some external sources call these ‘operation nodes’ or ‘sandbox handlers’, but here we use ‘policy node’ to refer to any node (filter or decision) in the policy graph.”
5. Add a note in the introduction or preamble: “We use ‘sandbox profile’ and ‘sandbox policy’ interchangeably: a profile refers to the static rules, and it becomes a policy when applied to a process.”

### Orientation.md
6. In the Stage 3 (Compiled → Kernel) section, add a footnote or inline note after describing `sandbox_apply`: “On macOS 14 and later, unprivileged use of `sandbox_apply` is blocked by System Integrity Protection (SIP) and will return EPERM unless the process has special entitlements.”
7. Somewhere in the introduction or where `sandbox-exec` might be assumed, add: “The `sandbox-exec` tool is no longer functional on macOS 14 and later; attempts to use it return an ‘Operation not permitted’ error.”

### Appendix.md
8. In the DSL cheatsheet or filter syntax section, add an example of a parameterized rule using `(param "name")` and `string-append`. Briefly explain how parameters must be provided when compiling, referencing system profiles.
9. In the “iOS 7–9 Graph-Based Formats” section, where “Operation Node Pointers” are introduced, rename or annotate as: “Operation Node Pointers (also known as Operation Pointer Table)” to align with Concepts.md terminology.
10. In the binary format section, add a note: “On macOS 14, compiled profiles may have `re_table_offset = 0`, indicating a new format variant. Decoders should not assume this offset is always nonzero.”
11. In the policy storage/history section, add: “On macOS 14 and later, sandbox profiles are stored as `.sb` files in `/System/Library/Sandbox/Profiles/`, removing the need to extract them from the kernelcache.”
