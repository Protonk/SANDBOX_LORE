# Reverse Engineering Plan (Sandbox-private 14.4.1-23E224)

## Inventory & relevance

- `Sandbox-private/14.4.1-23E224/kernel/BootKernelExtensions.kc`  
  Kernel collection containing `com.apple.security.sandbox` (Sandbox.kext) and associated MACF hooks.  
  - Can answer: PolicyGraph layout (node/tag structs, edges, decision/log bits), op pointer table structure, filter dispatch, kernel-side evaluation paths.
  - Cannot directly answer: how entitlements select profiles or how SBPL templates are expanded in userland.

- `Sandbox-private/14.4.1-23E224/userland/libsystem_sandbox.dylib`  
  Userland sandbox library (SBPL compiler, sandbox_init/apply/check APIs).  
  - Can answer: op/filter vocab tables, SBPL compile/load/apply call surfaces, profile header/loader struct layouts, parameter plumbing for `(param ...)` and possibly entitlement integration points.
  - Does not contain: the kernel PolicyGraph evaluator itself.

- `Sandbox-private/14.4.1-23E224/profiles/Profiles/*.sb`  
  SBPL source snapshots for system/App Sandbox profiles.  
  - Can answer: high-level policy (allow/deny, params, metafilters, macro/extension usage), which ops/filters appear in templates.
  - Cannot by themselves reveal: actual numeric op IDs, filter IDs, or compiled graph node layouts without alignment to compiler/runtime.

- `Sandbox-private/14.4.1-23E224/profiles/compiled/com.apple.TextEdit.sandbox.sb.bin`  
  Compiled TextEdit container profile, extracted from `SandboxProfileData` on this host/build.  
  - Can answer: concrete header fields, op table layout, literal/regex tables, and node encoding for at least one real App Sandbox profile.
  - Cannot alone answer: all possible node/tag variants or all op/filter combinations used platform-wide.

- `Sandbox-private/14.4.1-23E224/meta/SYSTEM_VERSION.txt`  
  Provenance (macOS version and build) for these artifacts; useful for tagging everything else.

---

## Goals

### Kernel-side (BootKernelExtensions.kc / Sandbox.kext)

- Recover PolicyGraph node/tag structs:
  - Identify tag values.
  - Determine field ordering and sizes for edges, operands, and decision/logging bits.
- Recover the operation pointer table:
  - Map op ID → PolicyGraph entry node/offset.
- Recover filter dispatch:
  - Map filter ID → evaluator function.
  - Infer argument schemas from how evaluators consume node fields and literal/regex tables.
- Anchor at least some of the above to observable behavior (eventually, via probes) so tag/flag interpretations are not purely speculative.

### Userland / compiler-side (libsystem_sandbox.dylib)

- Map op/filter vocab:
  - Extract op ID ↔ name and filter ID ↔ name, plus any metadata available in userland tables.
- Understand compile/load/apply pipeline:
  - Identify SBPL compilation entrypoints and profile loader(s).
  - Recover compiled profile header struct layout and any per-profile metadata (version fields, counts, offsets).
  - Identify parameter plumbing (how `(param ...)` inputs and possibly entitlements are passed into the compiler/loader).
- Clarify userland’s role vs kernel’s:
  - What is finalized in userland (macro expansion, parameter substitution).
  - What is only represented in kernel PolicyGraphs.

### Profile-side (SBPL + compiled TextEdit blob)

- Summarize SBPL templates:
  - For each `.sb`: default decision, params, operations, metafilters, extensions/macros.
- Align SBPL and compiled representation:
  - Use `com.apple.TextEdit.sandbox.sb.bin` as a concrete compiled profile to:
    - Validate inferred header fields and offsets.
    - Cross-reference operations and filters with SBPL summaries and op/filter vocab.
  - Use this as a template for future compiled profile decoding when additional blobs are available.

---

## Inputs we already have

- Kernel-side:
  - `Sandbox-private/14.4.1-23E224/kernel/BootKernelExtensions.kc`

- Userland-side:
  - `Sandbox-private/14.4.1-23E224/userland/libsystem_sandbox.dylib`

- Profile-side:
  - `Sandbox-private/14.4.1-23E224/profiles/Profiles/*.sb`
  - `Sandbox-private/14.4.1-23E224/profiles/compiled/com.apple.TextEdit.sandbox.sb.bin`

- Metadata:
  - `Sandbox-private/14.4.1-23E224/meta/SYSTEM_VERSION.txt`
  - `dumps/ghidra.md` (notes on desired RE coverage and tool usage)

---

## Ghidra automation plan (headless scripts)

General constraints:

- Prefer headless Ghidra scripts and batch jobs that emit machine-readable data (JSON/YAML/CSV) into `dumps/` or adjacent derived-data locations.
- It is acceptable to “over-collect”: broad scans and exports are fine; later passes can filter and interpret.
- Avoid relying on manual GUI exploration for anything that can be encoded as a script.

### Kernel (BootKernelExtensions.kc)

1. **Load and isolate Sandbox.kext**
   - Script: open `BootKernelExtensions.kc` and locate the `com.apple.security.sandbox` image.
   - Export:
     - Symbol list (including unnamed/auto-labeled functions).
     - String table.
   - Emit a symbol/strings dump for later text-based and structural searches.

2. **Locate PolicyGraph evaluator and tag switch**
   - Script: search for a large dispatch function that:
     - Accepts a “node” struct pointer.
     - Switches or branches on a node tag field.
   - Infer:
     - Tag field offset and size.
     - Per-tag handler entrypoints.
   - Emit:
     - A JSON map of tag → handler function, plus preliminary guesses about node struct layout.

3. **Recover node/tag struct layout**
   - For each tag handler:
     - Inspect how fields of the node are dereferenced (e.g., jumping to other nodes, indexing literal/regex tables).
   - Infer:
     - Edge field(s) (next-node offsets/indices).
     - Operand fields (indices into literal/regex tables or immediate values).
     - Decision/logging bits and any other flags.
   - Emit:
     - A tag layout map describing each node type’s fields and semantics.

4. **Recover operation pointer table**
   - Script: identify kernel code that:
     - Takes an op number and looks up an entry in some per-profile or global op-table structure.
   - From that:
     - Recover op-table base and size.
     - Map op ID → entrypoint node/offset in the PolicyGraph.
   - Emit:
     - An op entrypoint map suitable for correlating with userland op names and SBPL ops.

5. **Recover filter dispatch**
   - Script: locate code that:
     - Given a filter ID or node type, calls a particular evaluator or compares values to implement filter semantics.
   - Infer:
     - Filter ID → evaluator function relationships.
     - Argument shapes (e.g., path literal vs regex index vs numeric mask) based on how node fields and literal/regex tables are accessed.
   - Emit:
     - A filter dispatch map including function addresses and any argument-schema hints.

### Userland (`libsystem_sandbox.dylib`)

1. **Extract op/filter vocab tables**
   - Script: locate arrays or descriptor tables for operations and filters (e.g., `_operation_info`, `_operation_names`, `_filter_info`).
   - Emit:
     - Operation vocabulary catalog: IDs, names, and any auxiliary metadata.
     - Filter vocabulary catalog: IDs, names, and argument kinds/schema hints.

2. **Compile/load/apply pipeline**
   - Script: identify and cross-reference:
     - SBPL compilation entrypoints.
     - Functions that load compiled profiles from memory/disk.
     - Any publicly or privately named `sandbox_*` APIs (sandbox_init, sandbox_apply, etc.).
   - Infer:
     - Compiled profile header struct layout (fields, types, offsets).
     - Key offsets like op table, literal/regex tables within the compiled blob.
     - Parameter dictionaries or similar structures used to implement `(param ...)`.
   - Emit:
     - A header/loader struct description and any discovered constants relevant to compiled profile format.

3. **Parameter and entitlement plumbing**
   - Script: search for code that:
     - Uses parameter names known from SBPL templates.
     - References entitlement-related strings or keys.
   - At this stage, only document:
     - Where parameters enter the compile/load path.
     - Any clear connections between parameters and profile selection or specialization.
   - Emit:
     - A minimal map of parameter-related entrypoints and data structures for cross-referencing with SBPL.

### Profiles (SBPL + compiled TextEdit blob)

1. **SBPL summaries**
   - Script: for each `Profiles/*.sb`:
     - Parse profile name, default decision (deny/allow), operations used, metafilters, extensions/macros, and params.
   - Emit:
     - A profile summary catalog that can be joined with op/filter vocab and compiled-profile data.

2. **Compiled TextEdit profile decoding**
   - Non-Ghidra script (e.g., Python, Rust):
     - Treat `com.apple.TextEdit.sandbox.sb.bin` as a testbed.
     - Use inferred header layout from userland/kernel analysis to:
       - Parse header fields (version, counts, offsets).
       - Locate op table and literal/regex tables.
   - Once a minimally correct decoder exists:
     - Extend to walk the node graph and emit a normalized representation (nodes, edges, op mapping, literal/regex references).
   - Emit:
     - A structured graph dump for TextEdit suitable for comparison with:
       - SBPL summaries.
       - Kernel node/tag layouts.
       - Userland op/filter vocab.

---

## Desired data products

- An operation vocabulary catalog (op ID ↔ name, plus any available metadata such as groupings or comments) derived from userland tables. Persist this static artifact with other op vocabularies for the same OS/build.

- A filter vocabulary catalog (filter ID ↔ name, argument kind/schema hints, and any constraints implied by call patterns). Persist alongside the operation vocabulary and keep it keyed by OS/build.

- A PolicyGraph tag/layout map describing each node/tag type (field order, sizes, edge semantics, operand interpretation, decision/logging bits) inferred from the kernel evaluator. Persist this in the appropriate place in the graph/mappings layer so it can be reused by decoders and visualizers.

- An operation entrypoint mapping (op ID ↔ PolicyGraph entry node or offset) derived from the kernel’s operation pointer table. Persist with other graph-indexing metadata for this build.

- A filter dispatch map (filter ID ↔ evaluator function, plus any argument-handling patterns) derived from kernel or userland dispatch tables. Consider using this artifact to support internal tooling that validates filter argument shapes against SBPL usage.

- SBPL profile summaries (per `.sb` source: default decision, params, operations, extensions, metafilters) extracted into a compact machine-readable form. Persist with other SBPL-derived summaries so they can be joined with op/filter vocab and graph mappings.

- Compiled-profile descriptors for each `.sb.bin` blob (e.g., source app/profile, byte length, header fields as decoded, key offsets such as op table, literal/regex tables). Persist these as part of a “compiled profiles index” for the OS/build so decoders can locate and interpret blobs consistently.

- Optional graph dumps for selected compiled profiles (e.g., TextEdit): a normalized representation of operations, nodes, edges, and literal/regex references suitable for comparison against SBPL summaries and for use in higher-level analysis/visualization tools. Persist these in the graph/mappings area and clearly tie them back to their source blobs and SBPL templates.

---

## Open questions / uncertainty

- **Kernel collection layout:**  
  Precisely locating and isolating `com.apple.security.sandbox` within `BootKernelExtensions.kc` may depend on Ghidra’s KC loader behavior or external extraction tooling. If symbols are stripped or inlining is heavy, identifying the main PolicyGraph evaluator and op table may require heuristic control-flow and data-flow analysis.

- **Decision/logging bits vs tag encoding:**  
  It is not yet clear whether “allow/deny/log/no-log” semantics are encoded as separate fields or folded into tag values/flags. Static inference based on code paths and constants may need to be validated against runtime behavior (later, via probes) to avoid mislabeling node semantics.

- **Entitlement-to-profile selection:**  
  The mapping from entitlements and other process metadata to concrete profiles is likely implemented across multiple components (kernel exec hooks, AMFI, container management). The current artifacts emphasize kernel enforcement and userland compilation; they may not fully expose the policy that selects which SBPL/compiled profile is attached to a process.

- **Userland vs kernel responsibilities:**  
  Some macro and extension logic may be resolved in userland before compilation, while other structural invariants are only visible in kernel graphs. Distinguishing what is guaranteed by the format vs guaranteed by higher-level tooling remains an open modeling question.

- **Compiled profiles corpus:**  
  At present, only a single compiled profile (`com.apple.TextEdit.sandbox.sb.bin`) is available as ground truth. This is sufficient to validate header parsing and basic graph decoding for at least one App Sandbox profile, but may not cover all node/tag types or all op/filter combinations. Additional `.sb.bin` blobs can be added incrementally if needed, but are not required for the initial decoding work.
