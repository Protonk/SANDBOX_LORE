# mac-policy-registration – Research Report

## Purpose
Recover the sandbox/mac_policy_conf and mac_policy_ops (plus registration site) for this host baseline, across the kernel and sandbox kext slices.

## Baseline & scope
- Host: `world_id sonoma-14.4.1-23E224-arm64-dyld-2c0602c5` (Apple Silicon, SIP on).
- Inputs: kernelcache (`dumps/Sandbox-private/14.4.1-23E224/kernel/BootKernelCollection.kc`) with sandbox fileset entry rebuilt to `dumps/Sandbox-private/14.4.1-23E224/kernel/sandbox_kext.bin` (arm64e); analyzed Ghidra project `dumps/ghidra/projects/sandbox_14.4.1-23E224`.
- Out of scope: generic/macOS-cross-version claims; focus only on this world.

## Model (public anchor)
- `struct mac_policy_conf` (public headers): `mpc_name`, `mpc_fullname`, `mpc_labelnames` (all pointers, often NULL), `mpc_labelname_count` (u32 + padding), `mpc_ops`, `mpc_loadtime_flags` (u32), `mpc_field_off` (pointer), `mpc_runtime_flags` (u32), plus optional list/data pointers; registered via `int mac_policy_register(struct mac_policy_conf *mpc, mac_policy_handle_t *handlep, void *xd);`.
- Real kext examples (BlockBlock, Derpkit, etc.) show sparse population: `mpc_labelnames` often NULL, `mpc_labelname_count` = 0, `mpc_loadtime_flags` frequently `MPC_LOADTIME_FLAG_UNLOADOK` (0x2).
- Hard vs soft scan criteria:
  - Hard: candidate base inside `__DATA`/`__DATA_CONST`, pointer-sized alignment, slots readable, pointer-like fields are NULL or within this image, `labelname_count` small (<= 32).
  - Soft (ranked offline): printable ASCII for name/fullname when present, non-NULL ops pointer, loadtime flags in {0x2, 0x4, 0x6}, strings containing “sand/seat/policy”.
- Scan template (64-bit slots):
  0: name ptr (nullable)
  1: fullname ptr (nullable)
  2: labelnames ptr (nullable)
  3: u32 labelname_count (<= 32)
  4: ops ptr (nullable)
  5: u32 loadtime flags
  6: field_off / label slot ptr (nullable)
  7: u32 runtime flags
  8–9: optional list/data pointers (captured but not required)
- Experiment IR (per-candidate JSON):
```json
{
  "image": "com.apple.security.sandbox",
  "address": "0xffffff8000dead00",
  "segment": "__DATA_CONST",
  "slots": {
    "name": "0xffffff8000abc000",
    "fullname": "0xffffff8000abc100",
    "labelnames": "0xffffff8000abc200",
    "labelname_count": 2,
    "ops": "0xffffff8000def000",
    "loadtime_flags": "0x0",
    "field_or_label_slot": "0xffffff8000abc300",
    "runtime_flags": "0x0"
  },
  "string_values": {
    "name": "Sandbox",
    "fullname": "Seatbelt sandbox policy"
  }
}
```

## Deliverables
- `mac_policy_conf_candidates.json`: candidate structs (name/fullname/labelnames/ops pointers, segment/section, offsets).
- `mac_policy_conf_candidates_ranked.json`: offline-ranked shortlist (string/flag/ops hints) derived from the raw candidates.
- `registration_sites.json`: call sites (address, target, observed args) that appear to register sandbox/mac_policy_conf/mac_policy_ops.
- Notes on any linkage between mac_policy_ops and the op-table mapping for this world.

## Plan (initial)
1) Gather struct layout ground truth from host artifacts:
   - Extract mac_policy_* strings and walk XREFs to locate code that references them.
   - Identify data structures near those references that match a plausible mac_policy_conf layout (pointers to name/fullname/ops, etc.).
2) Sandbox kext surface:
   - Run string/import census over the sandbox kext slice.
   - Scan its `__DATA_CONST`/`__DATA` for structs matching mac_policy_conf shape; record candidates.
3) Registration trace:
   - From functions that reference mac_policy_* strings, record call sites and arguments that look like mac_policy_register-style calls.
   - Emit `registration_sites.json` with addresses, targets, and pointer args (conf/ops candidates).
4) Ops linkage check:
   - For any ops pointer found, compare table shape against `book/graph/mappings/op_table/op_table.json` using existing tools.
   - If alignment exists, note it; otherwise mark as non-op-table or unknown.

## Evidence & artifacts
- Ghidra project: `dumps/ghidra/projects/sandbox_14.4.1-23E224`.
- To be produced in this experiment: candidates and registration JSONs under `out/`.

## Status
- Rebuilt sandbox kext from `BootKernelCollection.kc` via `rebuild_sandbox_kext.py` (LC_FILESET_ENTRY `com.apple.security.sandbox`), fixing load-command offsets and producing an arm64e Mach-O (~90 MB) suitable for Ghidra import. Script now supports `--all-matching` (enumerate/rebuild fileset names containing sandbox/seatbelt); this world only exposes `com.apple.security.sandbox` (also emitted as `sandbox_kext_com_apple_security_sandbox.bin`).
- Scanner relaxed to hard-vs-soft checks (hard: data/const ranges, aligned readable slots, pointer-inside-image-or-NULL by default, `labelname_count` <= 32; soft: printable strings, ops presence, flag hints). Captures optional list/data slots and emits soft scores for offline ranking.
- Baseline scan (pointers constrained to image) yielded `candidate_count: 82`, `probe_points: 16495`, `bytes_scanned: 132195` (scan_slots=10) over `__DATA_CONST`/`__DATA`; all candidates had NULL name/fullname/labelnames/ops pointers, only flags varied.
- Pointer-range-relaxed calibration (`--script-args any-ptr`) yields `candidate_count: 118` with 36 candidates containing any non-zero pointer-like slot but still no printable strings and no in-image ops/labelnames; values appear as PAC-ish constants rather than a populated mac_policy_conf.
- Added offline filter `filter_conf_candidates.py`, emitting `mac_policy_conf_candidates_ranked.json` (post-relaxation run confirms only flag-heavy, pointer-null or pointer-out-of-image structs).
- `_read_ascii` guard added in the scanner to drop invalid pointers after a MemoryAccessException on the first arm64e run.

### Static kext search result (ok-negative)
- Scope: reconstructed all sandbox/seatbelt LC_FILESET_ENTRY slices for this world; only `com.apple.security.sandbox` exists.
- Method: ran `sandbox-kext-conf-scan` over `sandbox_kext.bin` (`__DATA_CONST` + `__DATA`) with pointer-constrained and pointer-relaxed templates based on the public `mac_policy_conf` layout (interleaved pointer slots for name/fullname/labelnames/ops plus small integer/flag fields).
- Findings:
  - Pointer-constrained pass: 82 candidates across ~132 KB / 16,495 probe points; all pointer slots NULL, only flag fields vary.
  - Pointer-relaxed pass: 118 candidates over the same region; 36 carry non-zero “pointer-like” values (PAC-looking), still no printable strings, no in-image ops/labelnames, no mac_policy_conf-like pointer pattern.
  - No additional sandbox/seatbelt fileset entries beyond `com.apple.security.sandbox`; same pattern across canonical and “any-ptr” runs.
- Claim: For `world_id = sonoma-14.4.1-23E224-arm64-dyld-2c0602c5`, there is no static `mac_policy_conf`-shaped structure in sandbox/seatbelt fileset kext data. Static kext scanning for `mac_policy_conf`/`mac_policy_ops` is status: ok-negative. Further registration/ops linkage work would require runtime evidence (live memory, tracing `mac_policy_register`), which is out of scope for this static-only surface.
