# SBPL Wrapper – Plan

Goal: provide a tiny helper that can apply an SBPL text file or a compiled `.sb.bin` to the current process (or a child) and run a command, so runtime-checks can exercise system profiles (airlock/bsd) and other compiled policies.

Approach: SBPL text application via `sandbox_init` is implemented in `wrapper.c` (`--sbpl <profile> -- <cmd>`). Binary-apply mode remains TODO.

Steps
1) **Binary mode (TODO)**
   - Add a `--blob <profile.sb.bin>` path that loads the compiled blob and applies it (via `sandbox_apply` or similar) before exec.
   - Handle errors and keep the CLI consistent with SBPL mode.

2) **Wire into runtime-checks**
   - Point `runtime-checks/run_probes.py` (or a sibling helper) at this wrapper for `sys:airlock`/`sys:bsd` entries in `expected_matrix.json`.
   - If using SBPL text from `sbdis`, keep shims minimal. If using blobs, ensure the apply path works on this host.

3) **Tests/Docs**
   - Keep the guardrail test (`tests/test_sbpl_wrapper_exists.py`) in sync.
   - Update README once blob mode lands and integration is done.
