# SBPL ↔ Graph ↔ Runtime – Research Report (Sonoma 14.4.1, arm64, SIP on)

## Aim
Produce SBPL → PolicyGraph → runtime “golden triples” on the Sonoma host, with expectation-aligned runtime logs (schema v0.1) keyed by `expectation_id`. Golden profiles must have coherent SBPL, decoded graphs, and runtime outcomes via `sandbox_init` from an unsandboxed caller.

## Current status (v0.1 cut)
- Golden triples (custom, allow-default, file-centric): `runtime:allow_all`, `runtime:metafilter_any`, `bucket4:v1_read`. For each: SBPL is simple; decoded graphs match intent; `static_expectations.json` (schema v0.1) carries expectation_ids; `runtime_results.json` matches expectations (OS perms on `/etc/hosts` writes are noted as outside sandbox scope).
- Platform-only apply-gated: `sys:bsd`, `sys:airlock`, `sys:sample` return EPERM/execvp at apply even unsandboxed; treated as platform-only, not harness bugs.
- Custom outlier: `bucket5:v11_read_subpath` still blocked with EPERM on deny probes; non-golden.
- Strict/apply-gate outliers: `runtime:param_path_concrete` (deny-default + process-exec) and `runtime:param_path_bsd_bootstrap` (deny-default + import `bsd.sb`) remain blocked at runtime (exec -6 or EPERM on subpath I/O). No strict profile is promoted in v0.1.

## Plan to close remaining gaps
- Lock v0.1 with the three golden custom profiles and explicit classifications for platform-only and outlier profiles (documented in Notes.md).
- Keep strict/apply-gate cases quarantined; if stricter coverage is needed later, design a broader bootstrap allow set (e.g., import `bsd.sb` plus targeted ops/paths) and rerun as a separate side-experiment without promoting to golden until runtime aligns with static expectations.
- Maintain artifacts in `out/`: compiled blobs, ingested summaries, static expectations (schema v0.1), runtime results keyed by `expectation_id`, and the manifest linking SBPL → blob → decode → runtime.

## Evidence & artifacts
- SBPL profiles under `profiles/`; compiled blobs and ingested summaries in `out/`.
- Static contract: `out/static_expectations.json` (schema v0.1, expectation_ids, entrypoint/terminal resolution flags).
- Runtime logs: `book/experiments/runtime-checks/out/runtime_results.json` emitted by `run_probes.py` with structured runtime_result/violation_summary fields.
- Manifest: `out/triples_manifest.json` (schema v0.1) linking SBPL → blob → ingested → runtime status.

## Status/Risk notes
- Golden profiles validated on this host; OS-level permissions (e.g., `/etc/hosts` writes) are outside sandbox scope and noted as such.
- Platform profiles are apply-gated by design; retain as platform-only examples.
- Strict/apply-gate profiles are known to fail runtime on this host; future strict work, if needed, should be run as a separate experiment branch.***
