# Agentic Access to the Sandbox Textbook

This document sketches a resource model and minimal API for agents and tools that need to work with the sandbox textbook as a living lab: chapters, concept graph, examples, decoded profiles, and capability catalogs.

The goal is to make the book and its companion repository *addressable* and *navigable* for agents without over-specifying protocols. Think in terms of resource types and operations, not wire formats.

---

## 1. Goals and Non-Goals

### 1.1 Goals

- Let agents:
  - **Explain**: answer questions in the book’s vocabulary, grounded in specific sections and artifacts.
  - **Locate**: map questions or concepts to relevant chapters, sections, and example artifacts.
  - **Demonstrate**: attach claims to concrete probes, app incarnations, decoded profiles, and catalogs.
  - **Compare**: summarize differences between apps or profiles using capability catalogs.

- Provide:
  - A small, stable set of **resource types** (text, concepts, artifacts, catalogs).
  - A simple set of **operations** on those resources (get, search, navigate graph, run selected tools).
  - A naming scheme that can be implemented as a local helper, a service, or a purely offline index.

### 1.2 Non-Goals

- No commitment to a specific transport (HTTP, CLI, notebook helper, etc.).  
- No attempt to expose every file or internal detail as a first-class API object.  
- No requirement that all tools are automated; humans can use the same shapes via scripts.

---

## 2. Core Jobs

The API is designed around four recurring jobs.

### 2.1 Explain

Given a question (e.g., “Why does this profile deny access to ~/Documents?”):

- Locate relevant **concept nodes** (operations, filters, profile layers, extensions).
- Fetch **sections** that define or use those concepts.
- Optionally pull in **artifacts** (capability catalogs, profile decodes) that demonstrate the behavior.
- Return a structured bundle that an agent can turn into an explanation with explicit references.

### 2.2 Locate

Given a term, snippet, or concept ID:

- Return:
  - Related **concepts**.
  - Related **sections** (chapters/sections where they are introduced or used).
  - Related **artifacts** (probes, app incarnations, profile decodes, catalogs).

This is “routing”: find where in the book+repo to work.

### 2.3 Demonstrate

Given a concept, claim, or example name:

- Locate **artifacts** (probes, example app incarnations, decoded profiles).
- Optionally invoke **tools** (e.g., run a probe, decode a profile) to regenerate boundary objects.
- Return structured outputs plus links back to concepts and sections.

### 2.4 Compare

Given two apps, profiles, or catalog entries:

- Retrieve or generate **capability catalog entries** for each.
- Compute differences at the level of operations, filters, entitlements, profile layers, and extensions.
- Return a comparison object that can be verbalized in the book’s vocabulary.

---

## 3. Resource Model

### 3.1 Resource Types

We will treat the universe as a small set of typed resources:

- `section` — A logically addressable span of textbook text.
- `concept` — A named, stable idea (e.g., `PolicyGraph`, `Profile Layer`, `Sandbox Extension`).
- `artifact` — A concrete technical object (example code, profile, decode, probe result, etc.).
- `catalog_entry` — A structured description of capabilities for a process/profile.
- `probe` — A runnable experiment definition (might be an `artifact` subtype).
- `profile_decode` — A structured representation of a compiled profile (headers, nodes, tables).
- `app_incarnation` — A specific build/mode of the example app (or TextEdit), with known sandboxing.

Implementation detail: in code, `artifact`, `probe`, `profile_decode`, and `app_incarnation` can be subtypes or tagged variants of a generic `artifact` resource.

### 3.2 Identifiers

Each resource should have a stable ID that is:

- Human-readable.
- Namespaced by type.

Examples:

- Sections: `ch4.3`, `ch6.3`, `appendix.A.2`
- Concepts: `concept:PolicyGraph`, `concept:ProfileLayer`, `concept:SandboxExtension`
- Artifacts:
  - `artifact:example-app/incarnation-A`
  - `artifact:example-app/incarnation-B`
  - `artifact:textedit/profile-main`
  - `artifact:probe/file-read-outside-container`
- Catalog entries:
  - `catalog:example-app/incarnation-A`
  - `catalog:textedit/main-app`
- Profile decodes:
  - `profile:example-app/incarnation-B-main`
  - `profile:textedit/app-sandbox`

IDs should be listed in a machine-readable index (e.g., `book/api/index.json`) and cross-referenced in `book/api/MAP.md`.

---

## 4. Surfaces and Operations

We define four “surfaces” agents can interact with: text, concept graph, artifacts, and tooling. Each has a minimal set of operations.

### 4.1 Text Surface (Sections)

**Resources:** `section`  
**Backed by:** Chapter files, conclusion, addendum.

**Operations:**

- `get_section(id)`  
  - Input: `section_id`  
  - Output: text blob, plus minimal metadata (title, chapter, related concept IDs).

- `find_sections(query)`  
  - Input: short text query or concept ID(s).  
  - Output: list of `section_id`s ranked by relevance.

**Notes:**

- Section IDs must be stable across minor edits.
- Each section should list primary concept IDs it uses/defines to tie into the concept graph.

### 4.2 Concept Graph Surface

**Resources:** `concept` and their relationships.  
**Backed by:** A compact knowledge graph derived from the “concepts” layer and references in chapters.

**Edges (examples):**

- `defines` (section → concept)
- `explains` (section → concept)
- `demonstrated_by` (concept → artifact)
- `uses` (artifact → concept)
- `relates_to` (concept → concept)

**Operations:**

- `get_concept(id)`  
  - Output: canonical definition (short), primary section IDs, related concept IDs.

- `neighbors(concept_id, relation_type?)`  
  - Output: set of IDs (concepts, sections, artifacts) connected by the given relation.

- `path(a, b)`  
  - Output: shortest or most “pedagogically plausible” path between concepts or between a concept and an artifact.

### 4.3 Artifact Surface

**Resources:** `artifact`, `app_incarnation`, `profile_decode`, `probe`, `catalog_entry`.

**Operations:**

- `get_artifact(id)`  
  - Output: typed object with metadata:
    - `type` (e.g., `app_incarnation`, `probe`, `profile_decode`)
    - `location` (path or reference)
    - `related_concepts` (IDs)
    - `related_sections` (IDs)
    - `related_catalog_entry` (ID, if any)

- `list_artifacts(filter_by_concept?, filter_by_type?)`  
  - Output: list of artifact IDs that match.

- `get_catalog_entry(id)`  
  - Output: structured catalog entry:
    - operations
    - filters
    - entitlements
    - profile layers
    - extensions
    - provenance (which profiles, which app incarnation)

**Notes:**

- Catalog entries should be normalized to a shared schema (see `book/api/CATALOG_SCHEMA.md`).
- The example app incarnations and TextEdit artifacts are first-class citizens.

### 4.4 Tooling Surface

This surface is optional at first but should be designed from day one.

**Logical tools:**

- `run_probe` — Run a predefined probe and collect results.
- `decode_profile` — Take a profile blob and produce a `profile_decode`.
- `summarize_capabilities` — Take a `profile_decode` (and context) and produce a `catalog_entry`.

**Operations:**

- `run_probe(probe_id, params?)`  
  - Output: probe result object, plus a new artifact ID for stored results.

- `decode_profile(profile_blob_ref)`  
  - Output: `profile_decode` object (or ID), plus links to relevant concepts and sections.

- `summarize_capabilities(profile_ref, context?)`  
  - Output: `catalog_entry` object (or ID).

**Notes:**

- In a minimal implementation, these can be “pseudo-ops” mapped to CLI scripts or notebooks.
- The plan should specify tool names and expected inputs/outputs in `book/api/TOOLS.md`.

---

## 5. Repository Integration

### 5.1 Index Files

Add a small set of index files under `book/api/`:

- `book/api/INDEX.json`  
  - Top-level listing of resource IDs and basic metadata (type, label, primary links).

- `book/api/SECTIONS.json`  
  - Map from `section_id` to:
    - file path
    - byte/line ranges
    - title
    - concept IDs

- `book/api/CONCEPTS.json`  
  - Nodes and edges of the concept graph.

- `book/api/ARTIFACTS.json`  
  - Map from artifact IDs to:
    - type
    - path or description
    - related concept/section/catalog IDs.

- `book/api/CATALOG_SCHEMA.md`  
  - Human-readable description of the catalog structure, aligned with code.

### 5.2 Naming Conventions

Document naming conventions in `book/api/NAMING.md`:

- Section ID patterns (`chX.Y`, `appendix.A.Z`).
- Concept IDs (`concept:<Name>`).
- Artifact IDs (`artifact:<namespace>/<name>`).
- Catalog IDs (`catalog:<namespace>/<name>`).

---

## 6. Phasing

### 6.1 Phase 0 — Static Maps Only

- Provide JSON indices and IDs.  
- No automated tools; agents can use the indices for “Explain” and “Locate” jobs.  
- The Addendum can point to these indices as a “machine-readable index.”

### 6.2 Phase 1 — Basic Tool Hooks

- Add CLI or notebook helpers that implement:
  - `run_probe`
  - `decode_profile`
  - `summarize_capabilities`
- Document expected inputs/outputs in `book/api/TOOLS.md`.

### 6.3 Phase 2 — Service Wrapper (Optional)

- Wrap the resource model and tools in a local or remote service:
  - Endpoints corresponding to the operations above.
- At this point, “agentic connectors” become concrete clients/glue around that service.

---

## 7. Documentation Stubs

The following companion documents should live alongside this plan:

- `book/api/MAP.md` — Human-readable overview of resource types, IDs, and where they live in the repo.  
- `book/api/CATALOG_SCHEMA.md` — Detailed schema for capability catalogs.  
- `book/api/TOOLS.md` — Description of the available tools and how they compose with the resource model.  
- `book/api/NAMING.md` — Naming and ID conventions for all resources.

`book/api/PLAN.md` (this file) is the architectural sketch; the other files are where concrete decisions and examples land as the API takes shape.
