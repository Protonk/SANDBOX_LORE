# SBPL ↔ Graph ↔ Runtime – Research Report

## Purpose
Demonstrate round-trip alignment between SBPL source, compiled graph structure, and runtime allow/deny outcomes on a small set of canonical profiles. Provide concrete triples that witness semantic concepts and tie into static/vocab views.

## Baseline & scope
- Host: TDB (record OS/build/SIP when runs are performed).
- Tooling: reuse `profile_ingestion.py` for decoding; use a lightweight probe harness (sandbox-exec or local runner) for runtime checks.
- Profiles: allow-all/deny-all, deny-except, filtered allow, metafilter, parameterized path.

## Deliverables / expected outcomes
- A small set of “golden” triples (SBPL source, decoded graph summary, runtime probe outcomes) for a few canonical semantic shapes on this host.
- `book/experiments/sbpl-graph-runtime/out/ingested.json` (and successors) capturing header/section summaries and decoded node/literal information for each profile.
- Runtime probe logs (e.g., ndjson files) tying specific probes to profile decisions, plus a manifest that links SBPL → blob → decode → runtime outcomes.
- Notes in this report and `Notes.md` describing any harness constraints or mismatches between decoded expectations and runtime behavior.

## Plan & execution log
### Completed
- **Current status**
  - Profiles authored: allow_all, deny_all, deny_except_tmp, metafilter_any (param_path pending param injection). Compiled to binaries with `sbsnarf.py` (absolute paths) and decoded via `profile_ingestion.py`; see `out/ingested.json` for header/section summaries (modern-heuristic).
  - Runtime probes: now using `book/api/SBPL-wrapper/wrapper --sbpl` plus a slim file-probe binary (`book/api/file_probe/file_probe`). `allow_all` behaves as expected. Strict `(deny default)` profiles (`deny_all`, `deny_except_tmp`, `metafilter_any`) still kill the probe with exit -6 even after adding `process-exec*`, `process-fork`, system path reads, and /tmp metadata allowances. Conclusion: micro-additions aren’t surfacing allow outcomes; to observe allow branches we need to relax defaults (allow default + explicit denies), which we haven’t yet applied here. System-style triples could include `bsd` (SBPL/compiled blob applies here); `airlock` is expected-fail locally.

### Planned
- Produce small “golden” triples (SBPL source, decoded graph, runtime probe outcomes) for a few canonical semantic shapes. Each triple should let us point from SBPL → compiled graph → observed allow/deny, exercising the semantic cluster and tying into static format and vocab.
  
  
  - Profiles: tiny SBPLs covering allow-all/deny-all, deny-except, single-filter allow, metafilter (require-any/all/not), and a simple param example.
  - Outputs: compiled blobs, decoded graph snippets (node IDs, filters, decisions), runtime probe logs (ndjson), and a manifest linking them.
  - Location: artifacts under `book/graph/mappings/runtime/` (or sibling) once stable; scratch outputs in `out/`.
  
  
  1) **Author profiles**
     - Write minimal SBPL files for each shape under this directory (e.g., `allow_all.sb`, `deny_except_tmp.sb`, `metafilter_any.sb`, `param_path.sb`).
     - Keep operations simple (file-read*, file-write*) and filters small (literal/subpath).
  
  2) **Compile and decode**
     - Use existing ingestion (`book/graph/concepts/validation/profile_ingestion.py`) to parse compiled blobs and emit JSON with op-table, nodes, and literals.
     - Extract node IDs/filters/decisions relevant to the probes into a concise summary per profile.
  
  3) **Run runtime probes**
     - Reuse/extend a harness (runner/reader or `book/api/SBPL-wrapper/wrapper --blob`) to execute a few file probes per profile, logging operation, path, exit, and errno to ndjson.
     - For environments where sandbox-apply is blocked, note the failure and prepare to rerun in a SIP-relaxed context.
     - Status: runtime probes now run via `book/api/SBPL-wrapper/wrapper --sbpl` with a slim file probe binary. Strict `(deny default)` profiles still kill the probe (-6) even after adding process-exec*/fork, system reads, and /tmp metadata; allows only surface when defaults are relaxed. System profiles: bsd is usable via SBPL/compiled blob; airlock is expected-fail locally (EPERM).
  
  4) **Link triple**
     - Build a manifest that ties SBPL → compiled blob → decoded nodes → runtime outcomes for each profile, with OS/build metadata.
  
  
  - At least 3 profiles with complete triples (source, decoded graph summary, runtime logs).
  - Manifest pointing to artifacts with OS/build and format variant.
  - Notes on any harness constraints (e.g., SIP) and next steps.

## Evidence & artifacts
- SBPL profiles under this directory (`allow_all`, `deny_all`, `deny_except_tmp`, `metafilter_any`, and planned param examples).
- Compiled blobs produced via `sbsnarf.py` and decoded with `profile_ingestion.py`; summaries in `out/ingested.json`.
- Runtime harness wiring (`book/api/SBPL-wrapper/wrapper --sbpl` plus `book/api/file_probe/file_probe`) used for initial probes.

## Blockers / risks
- Strict `(deny default)` profiles currently kill the probe binary (exit -6) even after adding additional allow rules for process and basic system paths, so allow branches are hard to observe without redesigning the profiles.
- System-style triples that include platform blobs must respect the same apply constraints seen elsewhere (`bsd` usable via SBPL/compiled blob; `airlock` expected-fail on this host), limiting how far this experiment can reach into platform behavior.

## Next steps
- Author and test additional profiles that relax defaults (e.g., `allow default` with explicit denies) so that allow and deny branches can both be exercised safely under the probe harness.
- Build and maintain a manifest that ties each profile to its compiled blob, decoded nodes, and runtime log files, with host/build metadata.
- Once a few stable triples exist, coordinate with `node-layout`, `op-table-operation`, and `runtime-checks` so these examples can serve as shared “golden” witnesses for SBPL/graph/runtime alignment.
# SBPL ↔ Graph ↔ Runtime – Research Report (Sonoma baseline)

## Purpose
Explore how small SBPL profiles with strict defaults behave when compiled and applied at runtime on this host. The focus is on understanding why some “deny default” profiles kill probes even when allowances are added, and on identifying profile shapes that yield clean allowed/denied triples for later “golden” examples.

## Baseline & scope
- Host: Sonoma baseline from `book/world/sonoma-14.4.1-23E224-arm64/world-baseline.json`.
- Inputs: tiny SBPL profiles under this directory, their compiled blobs, and decoder outputs.
- Tooling: `book.api.sbpl_compile`, `book.api.decoder`, and the SBPL wrapper / runtime harness used in `runtime-checks`.

## Deliverables / expected outcomes
- A small set of SBPL/compiled-profile/runtime triples that:
  - demonstrate strict and relaxed defaults,
  - show where allowances succeed or fail at runtime on this host.
- Notes in this Report and `Notes.md` explaining where strict profiles kill probes despite allowances and how more relaxed shapes behave.

## Plan & execution log
### Completed
- Experiment scaffolded (Plan, Notes, this Report).
- Initial strict “deny default” profiles compiled; runtime probes showed that these profiles kill probes even when allowances are added, confirming the baseline problem described in `Notes.md`.
- More relaxed profiles were introduced to keep probes alive long enough to observe allow/deny decisions; early results recorded as fragile and subject to harness limitations.

### Maintenance / rerun plan
As runtime harnesses stabilize, reuse this outline:

1. **Scope and setup**
   - Confirm the host baseline in `book/world/.../world-baseline.json`, this Report, and `Notes.md`.
   - Select a minimal set of SBPL profiles (strict vs relaxed) that are worth maintaining as examples.
2. **Compile and decode**
   - Recompile the chosen SBPL profiles and decode them with `book.api.decoder` to confirm structure has not drifted.
3. **Run runtime checks**
   - Apply the compiled profiles using the current SBPL wrapper harness and record runtime behavior for each probe.
   - Treat early termination or EPERM as first-class outcomes and document them here.
4. **Synthesize triples**
   - For profiles with stable behavior, record SBPL text, compiled profile summary, and runtime results as candidate “golden” triples.

## Evidence & artifacts
- SBPL source files and compiled blobs under this experiment directory.
- Decoder summaries in `out/` (where present) tying SBPL shapes to compiled graphs.
- Any runtime logs captured via the shared wrapper harness.

## Blockers / risks
- Strict “deny default” profiles on this host can kill probes even when allowances are added, making it hard to get clean allow/deny examples.
- Runtime harness changes (especially around apply gates and SIP) may invalidate earlier results; all runtime claims should be treated as `partial` or `brittle` until the harness is stable.

## Next steps
- Revisit these profiles once the runtime harness from `runtime-checks` is stable and bucket‑aligned.
- Promote a small number of SBPL/compiled/runtime triples into a “golden” set once behavior is consistent and reproducible.
