# Agents start here

This repo defines a fixed, opinionated “world” for the macOS Seatbelt sandbox and expects agents to stay inside it. All reasoning and code should be grounded in this world, not in generic or cross-version macOS lore.

---

## World and scope

- The world is a single host baseline:
  - macOS Sonoma 14.4.1 (23E224), Apple Silicon, SIP enabled.
- All architectural and behavioral claims are about this host unless explicitly labeled otherwise.
- Older sources (Apple Sandbox Guide, Blazakis, SandBlaster, etc.) are mediated through the substrate and experiments; they are not direct authorities.

---

## Substrate and vocabulary discipline

- Treat `substrate/` as the normative theory of Seatbelt for this host:
  - `Orientation.md` – lifecycle/story and high-level architecture.
  - `Concepts.md` – exact definitions (Operation, Filter, PolicyGraph, Profile Layer, etc.).
  - `Appendix.md` – SBPL, compiled formats, node structure, entitlements.
  - `Environment.md` – containers, neighboring systems (TCC, hardened runtime, SIP).
  - `State.md` – how the sandbox shows up on macOS 13–14 in practice.
- Answer questions and draft text using the project’s own vocabulary, not generic OS-security jargon.
- When you need a concept:
  - Prefer existing names from `substrate/Concepts.md` and `book/graph/concepts/CONCEPT_INVENTORY.md`.
  - If you believe a new concept is required, add it to the inventory (not ad-hoc) and state what evidence it is allowed to claim.

---

## Evidence model and mapping layer

- Static artifacts on this host are primary:
  - Compiled profiles, dyld cache extracts, decoded PolicyGraphs, vocab tables, and mapping JSONs under `book/graph/mappings/`.
- Experiments under `book/experiments/` and validation tooling under `book/graph/concepts/validation/` are the bridge between substrate theory and artifacts.
- Validation status is part of the meaning:
  - Treat `status: ok` / `partial` / `brittle` / `blocked` as semantic qualifiers; do not silently upgrade partial or blocked evidence to fact.
- Operation and Filter vocabularies:
  - Use only names and IDs defined in `book/graph/mappings/vocab/ops.json` and `filters.json`.
  - Do not invent new operation/filter names or assume cross-version stability without an explicit mapping.

When artifacts, runtime behavior, and substrate texts disagree, treat that as an open modeling or tooling bug. Record and bound the discrepancy; do not resolve it by averaging stories.

---

## Where to work

- `substrate/` – read-only theory; do not rewrite the world without an explicit modeling change.
- `book/` – textbook text, examples, and experiments:
  - See `book/AGENTS.md` for norms in this tree.
  - `book/graph/AGENTS.md` and `book/experiments/AGENTS.md` further constrain graph/mapping code and experiments.
- `status/` – audits and meta-level assessments (e.g., experiment audits); update when you change global expectations or norms.
- `dumps/` – reverse-engineering artifacts:
  - See `dumps/AGENTS.md` before running tools or adding files.
  - Binary/reverse-engineering work happens here; its *outputs* that become stable mappings should be promoted into `book/graph/mappings/` via experiments.
- `troubles/` – record crashes, decoding issues, and validation failures that need follow-up rather than fixing them silently.

---

## Things to avoid

- Do not:
  - Move, copy, or check in anything from `dumps/Sandbox-private/` into tracked directories.
  - Treat external knowledge (docs, blogs, your own model weights) as authoritative over the substrate and mappings for this host.
  - Introduce new mapping JSONs or change schemas under `book/graph/mappings/` without updating metadata and checking all known consumers.
  - Hide harness failures, decoder errors, or apply gates (e.g., `sandbox_apply` returning `EPERM`); record them in the relevant `Report.md` / `Notes.md`.
- When the simplest honest answer is “we don’t know yet” or “current evidence is inconsistent,” say that explicitly and point to the experiments or mappings that bound that ignorance.

If you stay within this world—substrate definitions, host-specific artifacts, and the existing concept inventory—your changes and explanations will fit cleanly into SANDBOX_LORE’s model of the macOS sandbox.
