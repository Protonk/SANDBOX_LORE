# Op-table vs Operation Mapping Experiment (Sonoma host)

Goal: empirically tie operation names (SBPL ops) to op-table entry indices and observed graph entrypoints in compiled profiles, so we can ground the “Operation vocabulary map” and per-operation graph segmentation claims. Keep everything reproducible and versioned using only local tooling and probes.

---

## 1. Setup and scope

- [x] Define the operation set to probe:
  - core filesystem ops: `file-read*`, `file-write*`
  - IPC: `mach-lookup` (fixed global-name e.g., `com.apple.cfprefsd.agent`)
  - network: `network-outbound`
  - baseline/no-op profile (deny default, no allows)
- [x] Create minimal SBPL profiles under `sb/`:
  - [x] Single-op profiles for each op above.
  - [x] Paired-op profiles that differ by exactly one operation (for delta analysis).
- [x] Add a slim wrapper (`analyze.py`) to emit:
  - `op_count`, `op_entries`
  - stride-12 tag counts and remainders
  - literal pool ASCII runs

Deliverables:
- `sb/*.sb` variants + compiled blobs under `sb/build/`.
- `out/summary.json` (per-variant structured data).
- A correlation artifact `out/op_table_map.json` that attempts to map op names → op-table index guess.

---

## 2. Data collection and correlation

- [x] Compile all `sb/*.sb` variants via libsandbox.
- [x] Run analyzer/wrapper to produce `out/summary.json`.
- [x] Build a simple correlation pass:
  - [x] Compare single-op vs paired-op profiles to see which `op_entries` value changes or appears.
  - [x] If op-table entries are uniform, record that and fall back to node/tag deltas for hints.
  - [x] Emit `out/op_table_map.json` keyed by profile → op_entries, plus inferred op→index notes.

---

## 3. Cross-check with semantic probes (optional stretch)

- [ ] Run existing semantic probes (e.g., `network-filters`, `mach-services`) with logging of SBPL op names and annotate traces with the op-table slot inferred from compiled profiles.
- [ ] Write `out/runtime_usage.json` with op names, any inferred op-table index, and observed behavior.

---

## 4. Documentation and reporting

- [ ] Keep running notes in `Notes.md` (dated entries).
- [ ] Summarize findings and remaining open questions in `ResearchReport.md`.
- [ ] Version all outputs by host/OS if needed (Sonoma baseline).

---

## 5. Open questions to resolve

- [ ] Which op name maps to the distinct op-table entry seen in mixed profiles (e.g., `[6,…,5]` in prior node-layout experiments)?
- [ ] Does the position of a non-uniform entry move when adding/removing specific ops?
- [ ] Can node/tag deltas (with uniform op-tables) provide secondary evidence for op→entry mapping?
- [ ] Does introducing filters/literals (e.g., subpath, literal) reintroduce the `[6,…,5]` divergence, and can we pin the lone entry to an op vocabulary slot?
