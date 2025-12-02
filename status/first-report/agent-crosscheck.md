## Context and scope

You (the human) asked a chat-style agent, with no direct involvement in the earlier Codex run, to **review the two new reports in `status/first-report/` for accuracy**. The prompt explicitly asked this agent to:
- Treat the Codex reports as hypotheses, not ground truth.
- Re‑investigate the repo independently (“burn tokens doing this again”).
- Compare the reports’ claims against the current state of experiments, mappings, validation outputs, and tooling.
- Report back on any mismatches, overstatements, or missing nuance.

Broadly, the plan I followed was:
- Re-read both `agent-readout.md` and `validation-status.md`.
- Walk the relevant parts of the tree again (`book/experiments`, `book/graph/mappings`, `book/graph/concepts/validation/out`, `book/api`, `tests/`) and open the key artifacts each report cites.
- For each major claim in the reports (per experiment, per cluster, per tool), check it directly against Plans, ResearchReports, and `out/*.json` files.
- Summarize where the reports are accurate, where they are incomplete, and where they are now stale or slightly misleading given the current repo state.

What follows is the detailed cross-check.

---

**Overall**

- I reread both `status/first-report/agent-readout.md` and `status/first-report/validation-status.md`, and re‑walked the repo (experiments, mappings, validation outputs, tooling) as if from scratch.
- Both reports are largely accurate and well‑aligned with the current substrate+book “world”, especially for static-format, vocab, and mapping work.
- The main inaccuracies are around how far the runtime/semantic validation has progressed and how some vocab “status” flags are represented.

---

**Where the reports are solid**

- **Experiments inventory:** The summaries of `anchor-filter-map`, `system-profile-digest`, `tag-layout-decode`, `vocab-from-cache`, `node-layout`, `field2-filters`, `probe-op-structure`, `op-table-operation`, `op-table-vocab-alignment`, `runtime-checks`, `sbpl-graph-runtime`, `entitlement-diff`, and `symbol-search` all match their `Plan.md`/`ResearchReport.md` and `out/` artifacts.  
  - Example: `anchor_filter_map.json` really does pin `/tmp/foo` and `/etc/hosts` to `path` (id 0), `/var/log` to `ipc-posix-name` (4), `idVendor` to `local-name` (6), and `preferences/logging` to `global-name` (5).
  - `tag_layouts.json` is exactly as described (12‑byte records, edges in fields[0,1], payload in field[2] for the listed tags).
  - `ops.json` has 196 ops and `filters.json` has 93 filters, harvested from the dyld cache as described in `vocab-from-cache`.
- **Op-table/vocab behavior:** The bucket summary in `agent-readout.md` lines up with `op_table_vocab_alignment.json`:
  - For profiles that explicitly mention them, `file-read*`, `file-write*`, and `network-outbound` indeed only use buckets {3,4} (checked by looking at op_entries at IDs 21, 29, 112 across those profiles).
  - `mach-lookup` (ID 96) uses buckets {5,6}, and bucket 6 appears only in mach+filtered‑read mixes, exactly as stated.
- **Concept inventory and validation wiring:** The description of concept clusters and the validation harness (static-format, semantic-graph, vocabulary-mapping, lifecycle-extension) matches `CONCEPT_INVENTORY.md`, `validation/Concept_map.md`, `validation/README.md`, `validation/tasks.py`, and `validation/out/index.json`.
- **Static-format & mappings:**  
  - `validation/out/static/{sample.sb.json,system_profiles.json}` and `validation/out/static/mappings.json` exist and have the shapes described.  
  - Guardrails in `tests/test_mappings_guardrail.py` enforce presence/shape of system profile digests, tag layouts, anchor map, and `field2_inventory.json` exactly as the reports claim.
- **Tooling:**  
  - `book.api.decoder` behaves as described in its README (preamble, op-table, tag-aware node list using `tag_layouts.json`, literal pool, sections).  
  - `book/api/SBPL-wrapper/wrapper.c` does support both `--sbpl` and `--blob` even though the README only documents `--sbpl`; the “README lags” note is correct.  
  - The Ghidra connector and `file_probe` usage in runtime harnesses match their READMEs and runtime logs.

---

**Issues and mismatches**

1. **Semantic-graph cluster is not purely “EPERM‑blocked” anymore**

   - `validation/out/index.json` still says:
     - `semantic-graph.status = "blocked"` and
     - `runtime_results.json` has `status: "sandbox_init EPERM (all probes denied)"` with `source: book/experiments/runtime-checks/run_probes.py`.
   - In reality, `validation/out/semantic/runtime_results.json` now contains **successful wrapper‑based runs** from `sbpl-graph-runtime`:
     - `allow_all.sb` probes all succeed (exit_code 0, rc=0).
     - `deny_all.sb` / `deny_except_tmp.sb` probes run and return rc=0 with **mismatched semantics** (expected deny but actual allow) rather than process death or EPERM.
   - `validation-status.md` repeats the older view:
     - “Blocked on runtime harness; only brittle sandbox-exec logs exist.”
     - “runtime_results.json records EPERM from sandbox_init despite wrapper attempts.”
   - That’s now too coarse:
     - There *are* EPERM‑blocked runs (runtime-checks) but also wrapper‑based runs that execute fine with semantic mismatches.
     - The semantic cluster is still not trustworthy as evidence, but it’s not “no runs at all / all EPERM” anymore.

2. **Source attribution for `runtime_results.json` is stale**

   - `validation/out/index.json` labels `runtime_results.json` as coming from `book/experiments/runtime-checks/run_probes.py`, and the new reports implicitly trust that.
   - The current `runtime_results.json` under `validation/out/semantic/` clearly reflects **`sbpl-graph-runtime`’s wrapper harness and `file_probe`**, not runtime‑checks’ `sandbox_runner`/`sandbox_reader`.
   - So the index (and by extension the new status reports) misattribute the source and oversimplify the failure mode.

3. **Mismatch between sbpl-graph-runtime ResearchReport and current runtime_results**

   - `sbpl-graph-runtime/ResearchReport.md` says strict `(deny default)` shapes “still kill the probe with exit -6”.
   - Current `validation/out/semantic/runtime_results.json` shows:
     - `deny_all.sb` and `deny_except_tmp.sb` probes run to completion with exit_code 0 and rc=0 (operations allowed), not exit -6.
   - `agent-readout.md` mirrors the older “kill the probe” story and doesn’t acknowledge the newer “profile applies but semantics are wrong” situation.

4. **Runtime-checks system profile behavior is more limited than phrased**

   - `agent-readout.md` says:
     - “System profiles now run as compiled blobs through the wrapper; on this host `sandbox_apply` returns EPERM for airlock; `bsd` works via SBPL/compiled blob.”
   - The actual `book/experiments/runtime-checks/out/runtime_results.json` shows:
     - `sys:bsd` and `sys:airlock` **both** fail blob apply via `wrapper --blob` (`sandbox_apply: Operation not permitted` for every probe).
   - The Notes do mention a separate path where `bsd` applies via `sandbox_init` on SBPL text, but:
     - Those `sandbox_init` runs are not reflected in `runtime_results.json` or the validation index.
     - The phrase “system profiles now run as compiled blobs through the wrapper” is easy to misread as “blob apply is working” when it currently isn’t; what’s true is “the harness is wired to try blob mode, but platform blobs are gated by `sandbox_apply` EPERM.”

5. **Vocab “status: ok” vs actual JSON fields**

   - Both reports talk about `ops.json` and `filters.json` having `status: ok` (and `check_vocab.py` asserting that), based on the `vocab-from-cache` reports and `validation/out/index.json`.
   - The actual JSON at `book/graph/mappings/vocab/{ops.json,filters.json}` and `validation/out/vocab/{ops.json,filters.json}` **do not contain a `status` field**; “status=ok” lives only in higher-level indexes and research notes.
   - `check_vocab.py` expects a `status` key and would currently fail against these files.
   - So, conceptually “vocab status is ok (196/93 entries)” is right, but the report overstates it as if `status` were a field inside the vocab JSON.

6. **“Only brittle sandbox-exec logs exist” is slightly too strong**

   - `validation-status.md` says for the semantic cluster: “only brittle sandbox-exec logs exist.”
   - In addition to those legacy `*.jsonl` logs, there is now a structured, wrapper‑based runtime dataset (`validation/out/semantic/runtime_results.json`) for SBPL micro‑profiles.
   - That dataset is *not* yet good semantic evidence (since many expectations don’t match), but it is **more than just sandbox-exec logs**, and the report doesn’t call that out.

7. **Minor phrasing / scope issues**

   - Static-format cluster is described as “largely validated”, which matches the structural coverage (headers, op-table slicing, tag layouts, system digests) but still leaves tail layout and per-tag semantics unsettled; the report does list those gaps explicitly, so this is more tone than a factual error.
   - Lifecycle/extension cluster: described as “partial” with only `entitlements.json` and `extensions_dynamic.md` in place, which matches `validation/out/lifecycle/` and the lack of runtime container/platform/extension evidence.

---

**Summary**

- The new reports are mostly faithful to the current static substrate, experiments, and mapping artifacts.
- The main inaccuracies are **time‑lagged summaries** around runtime/semantic validation and vocab “status” flags: they still reflect an older “everything runtime = EPERM or sandbox-exec” world, while the repo now contains partial wrapper‑based runs and some divergent behavior.
- If you revise these docs, the highest‑value fixes would be:
  - Updating the semantic cluster description to acknowledge the new `runtime_results.json` contents and clarify why they’re still not trusted as evidence.
  - Tightening the runtime-checks wording about `bsd` vs `airlock` and blob vs SBPL apply paths.
  - Either adding explicit `status` fields to the vocab JSON or softening the prose to make clear that “status: ok” comes from the validation index, not the files themselves.

