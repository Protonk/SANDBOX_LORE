# Inventory Validation Handoff (in-progress)

- **Plan + clusters:** `book/concepts/CONCEPT_INVENTORY.md` (Process stages 0–6).
- **Example mappings:** `book/concepts/EXAMPLES.md` (examples ↔ clusters).
- **Concept map:** `book/concepts/validation/Concept_map.md` (verbatim definitions + clusters).
- **Validation tasks:** `book/concepts/validation/tasks.py` (per-cluster tasks → examples → expected artifacts); helper `list_tasks()` prints a summary.
- **Harness notes:** `book/concepts/validation/README.md` (intended workflow; keep scripts under `book/concepts/validation/`).
- **Metadata collected:** `book/concepts/validation/out/metadata.json` (OS 14.4.1 build 23E224, arm64, SIP enabled; TCC/variant not collected).
- **Ingestion spine:** `book/concepts/validation/profile_ingestion.py` (minimal, variant-tolerant; recognizes legacy decision-tree headers, otherwise returns “unknown-modern” with full blob available for inspection).
- **Static outputs so far:** `validation/out/static/sample.sb.json` (from `book/examples/sb`) and `validation/out/static/system_profiles.json` (airlock.sb.bin, bsd.sb.bin from `extract_sbs` via ingestion helper); section lengths are placeholder for unknown-modern formats.
- **Semantic outputs so far:** `validation/out/semantic/metafilter.jsonl` (sandbox-exec runs: all cases returned exit 71/denied; expected allows did not succeed on this host), `validation/out/semantic/sbpl_params.jsonl` (both param/no-param runs exited 65; params likely unsupported), `validation/out/semantic/network.jsonl` (AF_INET/AF_UNIX probes all denied with EPERM).
- **Pending/failed probes:** `extensions-dynamic` segfaulted (`Sandbox(Signal 11)`), `entitlements-evolution` failed compile (PROC_PIDPATHINFO_MAX not defined), `mach-services` not run (requires multi-terminal setup), vocab/lifecycle logs not captured yet.

## Blockers and Resolutions (in progress)

- `extensions-dynamic`: `extensions_demo` still crashes with `Sandbox(Signal 11)` even after guarding null tokens. lldb could not attach (process exits immediately); dtruss blocked by SIP. Python/ctypes calls show `sandbox_extension_issue_file` returning `rc=0` with `token=NULL` for both protected (`/private/var/db/ConfigurationProfiles`) and `/tmp`, suggesting libsandbox may return success with null tokens for unentitled callers. Captured notes in `validation/out/lifecycle/extensions_dynamic.md`. Resolution pending (needs debugger with SIP disabled, different target, or mock issuance).
- `entitlements-evolution`: fixed buffer (added limits.h, sane path buffer); now builds and runs, logging unsigned metadata. Output captured in `validation/out/lifecycle/entitlements.json`. For full coverage, rerun with signed builds to see entitlement payloads.
- `mach-services`: compiled after falling back to `bootstrap_register`; registration failed with `kr=0x44c` (BOOTSTRAP_NOT_PRIVILEGED), and client lookups for demo/system services also returned `0x44c`. Logs in `validation/out/semantic/mach_services.jsonl`. Likely blocked by platform/bootstrap policy; would need an allowed service name or different launch context.
- Vocab/lifecycle logs: vocab not generated yet because ingestion of modern blobs is minimal; lifecycle logs captured for entitlements; extensions remain pending due to crash.
