# CONCEPT_INVENTORY.md

## Purpose

Make the core Seatbelt concepts explicit and enumerable. Provide one canonical “home” per concept to link, track, and validate: 
- Definitions
- Evidence
- Shared abstractions

## Win condition

Concretely, “success” means that each concept has:
1. **Witnesses**
- One or more *witnesses* where a witness is something concrete that constrains how the concept can be implemented or argued about: a parsed profile, a small SBPL snippet, a probe run, a log, etc.
2. **Explicit evidence types**
- We know which kinds of evidence are relevant:
  - Static structure (what we can see in compiled profiles or binaries).
  - Dynamic behavior (what happens when we run code under a sandbox).
  - Cross-references (how names and IDs line up across sources).
3. **Stable and tractable mappings**
- We can fix in a machine-readbale form:
  - How concepts map to example code.
  - How concepts map to shared abstractions.

## Concept Clusters by Evidence Type

To keep validation manageable, we group concepts by the kind of evidence that most naturally supports them. These *concept clusters* are not philosophical categories; they are “how can we actually see this?” categories.

### Static-Format Cluster

**Purpose**

These concepts are about how profiles look when compiled and stored: the concrete bytes and structures that the kernel and libraries consume, and the canonical binary IR that ingestion produces.

**Representative concepts**

- Binary Profile Header  
- Operation Pointer Table  
- Regex/Literal Table  
- Profile Format Variant

**Primary evidence**

- Captured compiled profiles (system profiles, small hand-compiled profiles, profiles emitted by tooling).
- Parsers that map blobs into typed structures.
- Structural invariants:
  - Offsets and sizes line up.
  - Operation tables and their indices are consistent.
  - String/regex tables are referenced correctly.

**Validation implications**

- A single “profile ingestion” spine can serve the entire static-format cluster:
  - Input: raw profile blobs.
  - Output: typed structures (a canonical PolicyGraph / node IR) plus a set of invariant checks.
- For each static-format concept, the concept inventory should point to:
  - The relevant parser or ingest module.
  - The invariants that are asserted.
  - The example profiles that are used as witnesses (e.g., specific system profiles, minimal synthetic profiles).
- All static-format evidence should record the profile format variant and OS/build it was taken from, so that later clusters can key vocab and behavior against the same versioned formats.

---

### Semantic Graph and Evaluation Cluster

**Purpose**

These concepts describe how the sandbox decides what to allow or deny: operations, filters, decisions, and the structure of the policy graph.

**Representative concepts**

- Operation  
- Filter  
- Metafilter  
- Decision  
- Action Modifier  
- Policy Node  
- PolicyGraph

**Primary evidence**

- Small, focused profiles or profile fragments that encode particular semantic shapes:
  - Allow-all / deny-all.
  - “Deny except X.”
  - “Allow only if regex/path filter matches.”
- Probes that:
  - Run under those profiles.
  - Attempt a small, explicit set of operations (file opens, network calls, IPC, etc.).
  - Record which actions succeed or fail.

**Validation implications**

- We want a “microprofile + probe” pattern:
  - For each semantic scenario, there is a tiny profile and a tiny test program/script.
  - The probe logs the attempted operations and outcomes in a structured way (e.g., JSON).
- A single evaluation harness can run these microprofiles and collect evidence:
  - For each run, we know which operations were attempted, which filters were relevant, which decision node in the ingested PolicyGraph was reached, and how that path maps back to SBPL structure.
- For each semantic concept, the concept inventory should point to:
  - Which scenarios (profiles + probes) witness the behavior.
  - What invariants are being tested (e.g., “filters of type X must cause Y under condition Z”).
- When probe outcomes are used as semantic evidence, they should distinguish Seatbelt decisions from adjacent controls (TCC, SIP, hardened runtime) so we do not mis-attribute denials to the policy graph.

A single well-designed microprofile can often witness multiple concepts at once (operation, filter, decision, action modifier, policy node shape).

---

### Vocabulary and Mapping Cluster

**Purpose**

These concepts are about naming and alignment: how symbolic names and argument shapes relate to on-disk IDs and observed behavior.

**Representative concepts**

- Operation Vocabulary Map  
- Filter Vocabulary Map

**Primary evidence**

- Enumerations of operations and filters from multiple sources:
  - Documentation (Apple Sandbox Guide, etc.).
  - Reverse-engineering sources.
  - Live system profiles (extracted operation/filter tables).
  - Runtime logs from probes (which operation IDs / names actually get used).
- Cross-checks between:
  - Our canonical vocab tables.
  - Tables extracted from compiled profiles.
  - The operation and filter names referred to by examples and probes.

**Validation implications**

- A “vocabulary survey” pipeline can consolidate and check vocab knowledge:
  - Gather all op/filter names and IDs from available sources.
  - Normalize them into canonical tables keyed by OS/build and, where applicable, profile format variant.
  - Mark each entry with status (known, deprecated, unknown, 14.x-only, etc.) and with provenance (which sources and artifacts support it).
- Example folders do not need to implement vocab logic themselves:
  - They should record which operations/filters they believe they are exercising (using canonical names).
  - A shared vocab-mapper can reconcile those names with IDs and on-disk representations.
- For each vocab-related concept, the concept inventory should point to:
  - The canonical vocab tables.
  - Any discrepancies or unknowns.
  - Tests or reports that compare different sources.
- Where possible, vocab entries should also point to microprofiles and probes that exercise a given operation or filter, tying names and IDs to concrete behavior.

This cluster ensures that when we say “operation X” or “filter Y,” we can trace that name from source snippets, to IDs in compiled profiles, to behavior observed at runtime.

---

### Runtime Lifecycle and Extension Cluster

**Purpose**

These concepts concern when and how profiles apply over a process lifetime, how layers compose into an effective policy stack, and how extensions and adjacent controls modify effective policy.

**Representative concepts**

- Sandbox Extension  
- Policy Lifecycle Stage  
- Profile Layer (in the sense of system/global/app layering)  
- Policy Stack Evaluation Order  
- Compiled Profile Source  
- Container  
- Entitlement  
- Seatbelt label / credential state  
- Adjacent controls (TCC service, Hardened runtime, SIP) insofar as they intersect with sandbox outcomes

**Primary evidence**

- Scenario-style probes that:
  - Launch processes through different paths (launchd services, GUI app launch, sandbox-exec, etc.).
  - Observe system behavior at distinct lifecycle points (e.g., pre-init, post-init, after extensions are granted).
  - Track how access changes over time in response to extensions and profile changes.
  - Inspect which compiled profiles and extensions are attached to a process label at each stage, and which containers and adjacent controls are in play.

**Validation implications**

- These concepts likely require fewer, more complex examples:
  - Each scenario can witness multiple lifecycle concepts simultaneously.
- They can reuse:
  - The same static ingestion tools (to see what profiles/extensions exist).
  - The same operation/decision probes from the semantic cluster (but applied at different lifecycle stages).
- For each lifecycle concept, the concept inventory should point to:
  - Which scenarios illustrate the lifecycle transitions.
  - What kinds of extensions or profile layering are being exercised.
  - Which compiled profile sources, containers, entitlements, and adjacent controls were active for that scenario, with OS/build recorded so that behavior can be tied back to specific platform states.

This cluster is more “macro” than the others, but aligning it with shared ingestion and probe tooling keeps it from becoming a separate universe.

---

## Misconceptions

The point of building a concept inventory and a validation plan is straightforward: every important idea about the sandbox needs something concrete under it. For each “operation,” “filter,” “policy graph,” or “extension,” we want to be able to say what artifacts and behaviors show that we understand it correctly on current macOS. That is why we bothered to group concepts and sketch validation modes at all—static ingestion to see how profiles are really encoded; microprofiles and probes to see how decisions are really made; vocabulary surveys to see how names and IDs really line up; lifecycle scenarios to see when and how policies really apply.

Once we take that stance—“a concept is only as good as the evidence that constrains it”—a problem appears. We are not just challenged by ignorance; hallucinating something false about the sandbox can be more troublesome than admitting we do not know. A clean-looking test, table, or diagram built on the wrong mental model will happily “confirm” that model. If you quietly assume that the SBPL text you see is the whole policy, or that each syscall matches one operation, or that layers simply intersect as “most restrictive wins,” you can design validation that seems careful and still leads you away from how the system actually behaves.

The next examples walk through a small set of “fair” misconceptions—plausible, technically informed ways to be wrong about profiles, operations, filters, layers, and extensions—and show the kinds of errors they produce. Each one looks sensible in isolation, lines up with how other systems work, and can be reinforced by partial evidence—yet they will assuredly lead you astray.

### SBPL Profile

**Misconception**

“An SBPL profile is *the* policy for a process: if I read the profile text, I see the full effective sandbox.”

This treats the SBPL file (or snippet) as a self-contained, complete description of the sandbox, ignoring that:

* The effective policy can be a composition of multiple profiles (system base profile, app/container profile, service-specific overlays).
* Some behavior comes from implicit or generated rules (e.g., containerization, platform defaults), not explicitly written SBPL.

**Resulting error**

You might confidently claim:

> “If operation X is allowed in this SBPL, the process can always perform X.”

Then you design a probe that:

* Runs under a containerized app profile that is layered on top of the SBPL you’re looking at, or
* Picks a system service whose effective policy has extra hidden constraints.

Your probe reports “denied,” and you incorrectly attribute that denial to a failure in your understanding of the SBPL syntax, rather than to stacked profiles and implicit rules you never accounted for.

---

### Operation

**Misconception**

“Each syscall maps to exactly one sandbox ‘operation’, and those names are just thin labels over syscalls.”

This flattens the abstraction:

* Operations can be broader than a single syscall (e.g., multiple syscalls hitting the same operation).
* A single syscall can trigger multiple operations, or an operation can be consulted in contexts that don’t look like a single obvious syscall boundary.
* Operations sometimes correspond to higher-level notions (e.g., `file-read-data`, `mach-lookup`) rather than raw kernel entry points.

**Resulting error**

You assume:

> “If `open(2)` fails due to the sandbox, that means the `file-read-data` operation is denied.”

Then you:

* Design probes and documentation that equate “open denied” ⇔ “operation A denied,” and “open allowed” ⇔ “operation A allowed.”
* Use that equivalence to build a capabilities table.

Later you discover cases where:

* `open` fails for reasons tied to different operations (e.g., metadata-only access, path resolution, or a Mach-right precondition), or
* A different syscall hitting the same operation gives a different denial pattern.

Your whole mapping from “observed syscall outcomes” to “operation-level policy” ends up misleading, and you over- or under-estimate the scope of particular operations.

---

### Filter

**Misconception**

“Filters are simple ‘if-conditions’ that are checked once per rule; if the key/value matches, the rule fires, otherwise it’s ignored.”

This treats filters as a one-shot guard on a flat rule list, instead of:

* Nodes and edges in a graph where unmatched filters can route evaluation to other nodes.
* Something that can be evaluated in multiple stages, with default branches and combinations, not just “test and drop rule.”

**Resulting error**

You explain filters as:

> “Think of filters like `if (path == "/foo") then allow; else ignore this rule`.”

Then you:

* Try to “prove” that a certain dangerous path is unreachable because every rule with that path filter looks safely denying/allowing in isolation.
* Ignore how non-matching filters might send evaluation along a default edge that reaches a permissive decision for broader paths.

You miss an allow-path that emerges from graph structure (default edges, metafilters, fall-through) and state in your write-up:

> “Path /foo/bar is definitely denied in all cases,”

when in reality the graph structure allows it via a non-obvious route.

---

### Profile Layer / Policy Stack Evaluation Order

**Misconception**

“Multiple sandbox layers just combine as ‘most restrictive wins’ (a simple logical AND over allows/denies).”

This is an intuitive model, but:

* Real composition includes ordering, default paths, and sometimes explicit overrides.
* Some layers might introduce new operations/filters or default behavior that is not a pure subset of another.
* Extensions and dynamic changes can alter the stack in ways that do not look like a straightforward meet of policies.

**Resulting error**

You teach:

> “If any layer denies an operation, it’s denied overall; if all allow it, it’s allowed. Just think of layers as intersecting sets of permissions.”

Then you:

* Analyze a system profile + app profile + extension scenario under this AND model.
* Conclude that a certain sensitive operation is impossible because “layer B denies it.”

In practice, the effective evaluation order or an extension changes the decision path so that the deny in layer B is never reached (or is overridden). Your risk assessment or example explanation claims “this cannot happen,” when in fact it does under real evaluation order.

---

### Sandbox Extension

**Misconception**

“A sandbox extension is basically a ‘turn off sandbox here’ token; once you have one, the sandbox doesn’t really apply to that resource anymore.”

This conflates:

* Scoped, capability-like grants (often tied to a path or specific operation types) with a global disable.
* The idea that extensions can be time- or context-limited, or only affect certain operations, with a blanket exemption.

**Resulting error**

You describe extensions as:

> “If an app gets an extension for `/private/foo`, it can do anything there, sandbox be damned.”

On that basis you:

* Design probes that simply check “with extension present, can we read/write/delete everything under that path?” and treat any failure as “extension is broken” or “my understanding is wrong.”
* Overstate threat models in your teaching material (“leak one extension and the whole sandbox collapses”), ignoring narrower semantics.

You mischaracterize the scope of extensions (and thus both overestimate and misdescribe certain attacks), and you design validation that expects full removal of constraints, misinterpreting partial, correctly scoped behavior as surprising or inconsistent.

---

### Dangers

All of these misconceptions share a pattern: they compress a layered, data-structure-heavy, evaluation-order-sensitive system into something almost like a static ACL with a few predicates. That compression makes the sandbox seem easy to reason about and tempting to summarize with a few diagrams, tables, or one-off probes. That's a coherent but wrong model of the sandbox, and coherent wrong models are hard to dislodge.

If you believe “the SBPL I’m looking at is the whole story,” you will design both attacks and defenses around that single text artifact. For a defender, that can mean auditing one app’s profile and concluding an operation is safely denied, without realizing that a system base profile, a container profile, or a per-service override is also in play. For an attacker, it can mean over-focusing on clever SBPL tricks in one layer while ignoring a weaker, more permissive layer that is actually controlling the decision path. In both cases, you are not just missing details—you are steering your entire project around the wrong object.

## Process

The validation plan ties the examples in `book/examples/` to the four clusters. All harness code and task metadata live under `book/concepts/validation/` (see `validation/README.md` and `validation/tasks.py`). Each run should record OS/build and profile format variant so evidence stays versioned.

**Stage 0 — Setup and metadata**
- Record host OS/build, hardware, SIP/TCC state, and profile format variant cues before collecting evidence.
- Use the shared ingestion spine (`book/concepts/validation/profile_ingestion.py`) for all blob parsing to keep IR consistent across clusters.

**Stage 1 — Static-Format validation**
- Run `sb/run-demo.sh`, `extract_sbs/run-demo.sh`, and `sbsnarf`/`apple-scheme` as needed to produce modern compiled blobs; ingest them to JSON under `validation/out/static/` with headers/op-table/node/regex/literal sections plus variant tags.
- For legacy blobs, use `sbdis` + `resnarf` to slice headers, op tables, and regex blobs; note the early decision-tree variant explicitly.
- Assert structural invariants (offsets/lengths, table indices) via ingestion; failures get logged alongside the artifact.

**Stage 2 — Semantic Graph and Evaluation**
- Run microprofiles/probes: `metafilter-tests`, `sbpl-params`, `network-filters`, `mach-services` (server+client). For each, capture inputs (profile text/params), attempted operations, resolved paths/addresses, and allow/deny outcomes in JSONL under `validation/out/semantic/`.
- After each run, map outcomes back to ingested PolicyGraph node IDs/paths where possible (using the ingestion output) to show which filters/decisions fired.
- Annotate any TCC/SIP/platform interference explicitly so Seatbelt graph evidence is not polluted by adjacent controls.

**Stage 3 — Vocabulary and Mapping**
- From Stage 1 blobs, extract operation/filter vocab (name↔ID↔arg schema) into versioned tables under `graph/mappings/vocab/ops.json` and `.../filters.json`.
- From Stage 2 logs, collect observed operation/filter names and map them to IDs using the tables; flag unknown/mismatched entries. Store results in `graph/mappings/vocab/runtime_usage.json`.
- Each vocab entry should carry provenance (which blob/log) and OS/build/variant.

**Stage 4 — Runtime Lifecycle and Extension**
- Run scenario probes: `entitlements-evolution` (signed variants), `platform-policy-checks`, `containers-and-redirects`, `extensions-dynamic`, and `libsandcall` apply attempts.
- Capture entitlements/signing IDs, container roots and symlinks, extension issuance/consumption results, and apply failures with error codes. Log under `validation/out/lifecycle/` with OS/build and profile sources (platform/app/custom).
- Where possible, correlate observed behavior with attached profiles/extensions (e.g., via ingestion of compiled profiles used in the scenario) and note adjacent control involvement (TCC prompts, SIP denial).

**Stage 5 — Evidence index**
- Summarize produced artifacts per cluster in a machine-readable index (e.g., JSON manifest under `validation/out/index.json`) pointing to the static/semantic/vocab/lifecycle outputs and their provenance.
- Link concept entries to their witnesses by referencing this manifest, closing the loop from concepts → examples → evidence.

**Stage 6 — Prepare for handoff**
- Build a stateless summary of the content in `validation/` for an agent who will audit your work. They do not need explanation, context, or reasoning--they need a rich router to the code and linkages. Place this summary and routing in `concepts/INV_SUMMARY.md`.

## Experiment Feedback and Next-Step Hooks

This section consolidates cross-cutting feedback from experiments under `book/experiments/`, organized by concept cluster, and proposes next actions. Descriptive, not authoritative—refer to the substrate for norms.

### Operation / Operation Pointer Table / Operation Vocabulary Map

**Related experiments**

- `book/experiments/node-layout/`
  - Focus: slicing modern compiled profiles into preamble/op-table/node/literal segments; probing node layout via stride heuristics and SBPL deltas.
  - Key outcome: confirmed presence and rough placement of the operation pointer table and literal/regex pools; identified non-uniform op-table patterns like `[6,…,5]` in some mixed-operation profiles without resolving which operations those entries correspond to.
- `book/experiments/op-table-operation/`
  - Focus: mapping SBPL operation names to op-table entry “buckets” (small indices like 4, 5, 6) using synthetic profiles and shared ingestion helpers.
  - Key outcome: showed that unfiltered `file-read*`, `file-write*`, and `network-outbound` share a uniform bucket (4) while `mach-lookup` lives in another (5); adding filters/literals to read moves it to the mach-style bucket (5), and combinations of mach + filtered reads produce non-uniform `[6,6,6,6,6,6,5]` patterns.

**What we’ve learned so far**

- The operation pointer table is observable and behaves in a structured way even for tiny synthetic profiles:
  - Single-op and simple mixed-op profiles often collapse into a uniform op-table (all 4s or all 5s) across all entries.
  - Profiles that mention `mach-lookup` tend to use a different op-table value (5) and a higher `operation_count` than profiles without mach, even when the set of SBPL rules is small.
  - Adding certain filters/literals to `file-read*` (subpath, literal `/etc/hosts`) can move read into the mach-like bucket.
  - Specific combinations (mach + filtered read) can produce genuinely non-uniform tables like `[6,6,6,6,6,6,5]` with `operation_count=7`.
- Node-region tag counts and literal pools change in ways that correlate with these buckets:
  - “Bucket 4” profiles use one pattern of tags (e.g., {0,2,3,4}) and have empty or minimal literal pools.
  - “Bucket 5” and “bucket 6/5” profiles introduce tags {0,1,4,5,6} and carry path-like and mach-name literals with type prefixes.
  - This matches the substrate’s view that compiled profiles pool literals/regexes and route operations through different graph entry families depending on structure.
- Critically, we still lack:
  - A vocabulary-aware mapping from operation names to numeric operation IDs on this host.
  - An assignment of specific SBPL operations to the individual table entries in non-uniform patterns such as `[6,…,5]`.

**Why this aligns with the substrate**

- The substrate defines:
  - **Operation** as a symbolic class of kernel action in SBPL and its numeric ID in compiled profiles.
  - **Operation Pointer Table** as an indirection from operation IDs to PolicyGraph entry nodes.
  - **Operation Vocabulary Map** as a versioned map from names ↔ IDs ↔ argument schemas.
- The experiments respect these roles by:
  - Treating op-table entries as opaque indices (4/5/6) and only inferring **relative** behavior (which buckets appear, how they shift) rather than guessing absolute IDs.
  - Using SBPL deltas to see how changing operations and filters perturbs the op-table and node/literal structure, without over-claiming about hidden fields.
  - Producing structured artifacts (`summary.json`, `op_table_map.json`) that match the “validation pattern” described in Concepts (compile simple profiles; decode headers/op-tables; check structural invariants).

**Recommended next steps**

1. Finish targeted SBPL deltas (within op-table-operation).
   - Add single-op literal profiles and compare buckets:
     - `file-read*` with only `(literal "/etc/hosts")` (no mach, no subpath).
     - Mach-only profiles with and without associated literals (but no extra read rules).
   - Design profiles that:
     - keep literals but toggle mach on/off, and
     - keep mach but toggle filters (subpath vs literal) on/off.
   - Goal: determine whether the non-uniform `[6,…,5]` pattern is fundamentally:
     - “mach + filtered read,”
     - “read+filter complexity regardless of mach,” or
     - an artifact of `operation_count` and the profile’s internal layout.
2. Connect to the vocabulary-mapping validation cluster.
   - Use or extend the `vocabulary-mapping` tasks in `book/graph/concepts/validation/tasks.py`:
     - Ensure that `out/vocab/ops.json` and `out/vocab/filters.json` exist for this Sonoma host by extracting vocab tables from known system blobs (e.g., `extract_sbs` outputs).
     - Once those tables exist, revisit the op-table-operation artifacts and interpret 4/5/6 as actual operation IDs where possible.
   - This is the step where the experiment transitions from “bucket behavior” to a real **Operation Vocabulary Map** anchored in canonical artifacts.
3. Add a cautious correlation pass (after vocab exists).
   - Extend `book/experiments/op-table-operation/analyze.py` or add a sibling tool to:
     - Align op-table indices across all synthetic profiles.
     - Annotate which indices are consistently present in “mach-only” vs “read-only” vs “filtered read” profiles.
     - Use the operation vocabulary table to hypothesize which ID corresponds to each index on this host.
   - Keep this clearly documented as hypothesis-generating: the final word on vocab comes from canonical tables, not just these small experiments.
4. Optional runtime cross-checks.
   - Run selected semantic probes (`network-filters`, `mach-services`) under specific synthetic profiles and:
     - Log SBPL operation names and observed decisions.
     - Cross-check that profiles in the “mach bucket” behave as expected for mach-lookup (and differently for non-mach ops).
   - This ties the static op-table buckets back to observable runtime behavior, strengthening the Operation concept across SBPL, binary, and runtime layers.
5. Surface these results in concept/validation docs.
   - When updating concept or validation docs, reference these experiments as:
     - concrete evidence that op-table structure is sensitive to both operations and filters,
     - a template for SBPL-driven static validation of binary structures,
     - and a boundary marker: beyond simple bucket behavior, vocabulary mapping should defer to the dedicated `vocabulary-mapping` tasks and canonical artifacts.

### Vocabulary extraction (Operation/Filter)

**Related experiments**

- `book/experiments/vocab-from-cache/`
  - Focus: pull Operation/Filter vocab tables from the Sonoma dyld cache (Sandbox framework/libsandbox).
  - Key outcome: harvested `ops.json` (196 entries) and `filters.json` (93 entries) with `status: ok`, host/build metadata, and provenance; added a guardrail (`check_vocab.py`) to assert counts/status.
- `book/experiments/op-table-vocab-alignment/`
  - Focus: align op-table buckets from synthetic profiles with vocab IDs.
  - Key outcome: alignment artifact now populated with `operation_ids`, `filters`, and `filter_ids` per profile; `vocab_status: ok` recorded from the harvested vocab.

**What we’ve learned so far**

- The cache-derived vocab resolves the earlier “partial/unavailable” gap; operation_count is 196 (decoder heuristics that suggested 167 were incomplete).
- Op-table summaries can now carry concrete operation IDs and filter IDs, enabling bucket interpretation on this host.

**Recommended next steps**

1. Interpret bucket patterns with IDs: summarize, per bucket (4/5/6), which operation IDs appear across the synthetic profiles; record host/build/vocab hash.
2. Thread filter IDs into bucket shifts: use filtered profiles to note which filters (by ID) coincide with bucket changes, even if field2 mapping is pending.
3. Keep vocab guardrails in CI: run `check_vocab.py` to catch drift; regenerate alignment when vocab changes.
4. Feed concise findings back into the concept docs as evidence for versioned Operation/Filter Vocabulary Maps.

### Field2 / Node decoding / Anchor probes

**Related experiments**

- `book/experiments/field2-filters/`
- `book/experiments/node-layout/`
- `book/experiments/probe-op-structure/`

**Current state**

- Field2 mapping remains blocked by modern node decoding: stride-12 heuristics expose small filter-ID-like values but no literal/regex references.
- Anchor scans now include an `offsets` field and list anchors; with decoder literal_refs and prefix normalization, simple probes now produce node hits for anchors (e.g., `/tmp/foo` → nodes in `v1_file_require_any`). Literal/regex operand decoding is still heuristic and needs proper tag-aware layouts.
- Tag-aware decoder scaffold exists; literal references and per-tag layouts remain to be reverse-engineered.
- Anchor→field2 hints are published under `book/graph/mappings/anchors/anchor_field2_map.json` for reuse.

**Recommended next steps**

1. Prioritize a tag-aware node decoder: per-tag variable-length layouts with operands wide enough to carry literal/regex indices.
2. Once literals are exposed, rerun anchor scans to map anchors → nodes → field2 → filter IDs; add guardrails for key anchors.
3. Use system profiles (strong anchors) as cross-checks; document evidence tiers in the respective ResearchReports.
