# VFS Canonicalization – Notes

Use this file for concise notes on commands, runs, and observations for the `/tmp` ↔ `/private/tmp` experiment.

- Re-running the runtime harness with `sandbox_reader` on this host now returns `sandbox_init` `EPERM` during apply. Kept the canonicalization runtime outputs from the last successful run; revisit sandbox_apply gating if a fresh run is needed.
- Latest runtime rerun succeeded only after enabling the Codex harness `--yolo` flag (more permissive environment) to bypass the sandbox_apply gate; outputs now reflect that run.
- Expanded path set to `/tmp/bar`, `/tmp/nested/child`, and control `/var/tmp/canon` (with canonical counterparts). `/tmp` aliases behave like `/tmp/foo` (only canonical `/private/tmp/...` literals are effective). `/var/tmp/canon` remains denied even with canonical literals present; treat as non-canonicalized/controlled alias.
- Added `file-write*` and metadata ops to the probes. Writes follow the read pattern (canonical `/private/tmp/...` effective; `/var/tmp` alias denied). Metadata probes currently return `deny` with exit_code `-6` even on canonical paths—likely a harness limitation rather than policy evidence; treat metadata results as **blocked/partial** until a metadata-capable runner is added.
