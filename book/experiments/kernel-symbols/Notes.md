# Notes

- Ghidra outputs for kernel symbols/strings are relocated to `book/experiments/kernel-symbols/out/<build>/kernel-symbols/`.
- Use the connector helper `run_task.py kernel-symbols --exec` to regenerate; defaults include ARM64 processor and the disable-x86 pre-script.
- Keep using `--process-existing --no-analysis` for downstream scripts to avoid rerunning analyzers.
- Target extraction: `targets.json` (generated Dec 2 2025) under `out/14.4.1-23E224/kernel-symbols/` lists key sandbox-related strings/symbols:
  - Primary strings: `0x-7fffdf3a68` (`com.apple.kext.AppleMatch`), `0x-7fffdf10f0` and `0x-7ffd22d6e0` (`com.apple.security.sandbox`).
  - Sample mac_policy symbols: `_mac_policy_addto_labellist`, `_mac_policy_init*`, `_mac_policy_list*` at `0x-7ffc3fceaf` .. `0x-7ffc3fce10`.
- Data-define run (Dec 2): `run_data_define.py --address addr:0xffffff800020ef10 --process-existing --no-analysis --timeout 900` produced `data_refs.json` with the `com.apple.security.sandbox` TEXT string defined, zero callers/xrefs (as expected under no-analysis).
- Data-define Track A (no-analysis) batch (Dec 2): ran all 11 targets from `targets.json` with `--process-existing --no-analysis`; all returned with zero callers. `data_refs.json` overwritten each time.
- Data-define Track B (analysis) on `addr:0xffffff800020ef10` (Dec 2): re-ran without `--no-analysis` (~59s). Result still shows the string defined with zero callers (no refs surfaced even with analysis). Logged pcode warnings but run succeeded.
- String-refs run (Dec 2): `run_task.py kernel-string-refs --process-existing --exec` captured three string hits (two `com.apple.security.sandbox`, one `com.apple.kext.AppleMatch`), zero symbol hits, zero external libraries. References lists are empty. Output copied to `out/14.4.1-23E224/kernel-string-refs/string_references.json` (error.log in dumps reflects a pre-fix run).
