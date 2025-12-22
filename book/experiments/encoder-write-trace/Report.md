# Encoder Write Trace – Report

## Purpose

Join libsandbox encoder writes to compiled-blob bytes by tracing the internal
write routine during SBPL compilation. This is a static, userland witness: it
does **not** interpret kernel semantics or runtime policy decisions.

## Baseline & scope

- World: `world_id sonoma-14.4.1-23E224-arm64-dyld-2c0602c5`.
- Inputs: SBPL corpus under `book/tools/sbpl/corpus/`.
- Compile-only: no `sandbox_apply` runs.
- Evidence tier: mapped-but-partial (experiment-local join).

## Deliverables

- Interposer + harness:
  - `harness/sbpl_trace_interpose.c` (triage + hook strategies)
  - Entry-text trampoline patch derived from unslid address + runtime slide
  - `harness/build_interposer.sh` (build script)
  - `harness/mach_exc_server.c` / `harness/mach_exc_server.h` (MIG server stubs)
  - `harness/mach_exc_user.c` / `harness/mach_exc_user.h` (exception forwarding stubs)
  - `compile_one.py` / `run_trace.py` (runner)
- Outputs (under `out/`):
  - `triage/*.json` (hook triage per input)
  - `traces/*.jsonl` (write records)
  - `blobs/*.sb.bin` (compiled blobs)
  - `manifest.json` (inputs + outputs)
  - `summary.json` (counts + world_id)
  - `trace_analysis.json` (join analysis)
  - `trace_join_check.json` (network-matrix cross-check)

## Evidence & artifacts

- Interposer build: `book/experiments/encoder-write-trace/out/interposer/sbpl_trace_interpose.dylib`.
- Baseline compile smoke: `book/experiments/encoder-write-trace/out/blobs/_debug.sb.bin`.
- Trace outputs: `book/experiments/encoder-write-trace/out/traces/baseline_allow_all.jsonl` (hardware-breakpoint run).
- Join analysis: `book/experiments/encoder-write-trace/out/trace_analysis.json`.
- Join cross-check: `book/experiments/encoder-write-trace/out/trace_join_check.json`.

## Status

- Status: **partial**.
- Earlier dyld interpose load failed with `symbol not found in flat namespace '__sb_mutable_buffer_write'`,
  which suggests (but does not prove) the write routine is not exported/bindable.
- The harness records triage metadata (including callsite reachability) and supports
  dynamic interpose (if exported/bindable), address-based patching, or hardware-breakpoint
  tracing for internal callsites.
- A patch-mode viability run computed the runtime address and UUID match but failed to
  patch text pages with `mprotect failed: Permission denied`, yielding zero write hits.
  The patch path now falls back to `mach_vm_protect(..., VM_PROT_COPY)` but still fails
  with `(os/kern) protection failure`; these runs are recorded as hook failures rather
  than generic reachability errors.
- The patcher now uses a W^X-correct flow (RW then RX, no RWX) and records Mach VM
  region metadata. The target region reports `protection: r-x`, `max_protection: r-x`,
  and `max_has_write: false`, which is consistent with an immutable `__TEXT` mapping
  on this host. Patch mode now treats this as a terminal skip (`hook_status:
  skipped_immutable`) rather than attempting to write text pages.
- A hardware-breakpoint hook (Mach exception port + ARM_DEBUG_STATE64) now produces
  write records without modifying text. The baseline run (`baseline_allow_all`) yields
  226 write records in `book/experiments/encoder-write-trace/out/traces/baseline_allow_all.jsonl`
  with `hook_status: ok` in `book/experiments/encoder-write-trace/out/triage/baseline_allow_all.json`.
- `trace_analysis.json` reconstructs 416 bytes across 204 writes for the best buffer
  (`coverage: 410`, `match.kind: gapped`), with both cursor interpretations reporting
  the same best score for the baseline input.
- `trace_join_check.json` reports `status: ok` but skips all network-matrix pairs
  because only `baseline_allow_all` is present in the trace manifest.

## Running / refreshing

From repo root:

```sh
python3 book/experiments/encoder-write-trace/run_trace.py --mode triage
python3 book/experiments/encoder-write-trace/analyze_trace.py
python3 book/experiments/encoder-write-trace/check_trace_join.py
```

Note: triage mode records hook metadata under `out/triage/`. Traces require
`--mode dynamic` (exported/bindable), `--mode patch` with a known address/offset,
or `--mode hw_breakpoint` when patching is blocked by region max-protection.

## Blockers / risks

- We do not yet have triage output confirming export/bind status of the write
  routine. The dyld error is only a hint; the triage output is the witness.
- Dynamic interpose can only affect dyld-bound callsites; direct intra-image
  calls will require patching or an external tracer.
- Address-based patching appears blocked by region max-protection (`r-x` without write)
  even after switching to W^X-correct protection changes. The Mach VM region metadata
  in `out/triage/baseline_allow_all.json` is the current witness.
- The hardware-breakpoint hook currently arms the current thread; if compilation
  migrates to other threads, additional thread coverage may be required.
- The breakpoint PC check accepts the target address and the next instruction
  (`target+4`) to accommodate debug exception PC semantics; this is still tied to
  the target callsite but should be validated against additional inputs.
- Callsite reachability is inferred from the indirect-symbol table (`otool -Iv`)
  on the extracted libsandbox image; this is a partial proxy for dyld bind tables.
- dyld_info exports/imports are recorded as a convenience signal; the extracted
  libsandbox image may fail dyld_info parsing, so a host `/usr/lib` fallback is used.
- `DYLD_SHARED_REGION=private` did not clear the mprotect/VM_PROT_COPY failure;
  `avoid` aborts because core system dylibs are not present on disk when bypassing
  the shared cache.
- Attempting a non-shared-cache helper by loading
  `book/graph/mappings/dyld-libs/usr/lib/libsandbox.1.dylib` via `ctypes.CDLL`
  fails with a code-signature error ("Trying to load an unsigned library").
- A fresh libsandbox extracted with `extract_dsc.swift` (from the dyld shared cache)
  still fails ad-hoc signing (`main executable failed strict validation`), so the
  private-dlopen helper path is currently blocked by code-signature validation.
- DTrace pid-provider probing was attempted but blocked by SIP with "DTrace requires
  additional privileges".
- Even with a working hook, the cursor parameter may be an offset or a pointer;
  any join must remain explicit about this ambiguity.

## Next steps

- Run `run_trace.py --mode triage` to capture export/bind status and callsite
  reachability metadata in `out/triage/`.
- If the symbol is exported/bindable, try `--mode dynamic`; otherwise provide a
  stable address/offset and run `--mode patch`.
- Once more inputs are traced, rerun `analyze_trace.py` and `check_trace_join.py`
  to extend join coverage beyond the baseline manifest.
