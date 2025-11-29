# AGENTS.md — book workspace router

You are in `book/`, the Seatbelt textbook workspace. Use this as a router to find the right materials; it is not a workflow script.

- `Outline.md` — high-level book outline and chapter sequencing.
- `chapters/` — per-chapter drafts/plans; filenames match chapter numbers. Check local README/notes inside each chapter.
- `graph/` — Swift contracts and generated JSON for concepts/regions (`Sources/main.swift`, `Package.swift`, `concepts/`, `regions/`).
- `experiments/` — research clusters with `Plan.md`, `Notes.md`, `ResearchReport.md`, and `out/` artifacts (e.g., `runtime-checks`, `op-table-operation`, `node-layout`).
- `examples/` — runnable SBPL/demo bundles; indexed by `examples/examples.json`.
- `profiles/` — SBPL sources/builds used by chapters, examples, and experiments.
- `api/` — API planning/design notes (`api/PLAN.md`, etc.).
- `tests/` — guardrails for book artifacts and experiment outputs.

For canonical Seatbelt vocabulary or lifecycle framing, step up to `substrate/AGENTS.md`
