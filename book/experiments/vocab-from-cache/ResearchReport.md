# Vocab from Cache – Research Report (Sonoma / macOS 14.4.1)

## Purpose

Extract Operation/Filter vocab tables (name ↔ ID) from the macOS dyld shared cache (Sandbox.framework/libsandbox payloads) and align them with decoder-derived op_count/op_table data from canonical blobs, producing real `ops.json` / `filters.json` for this host.

## Scope and baseline

- Host: macOS 14.4.1 (23E224), kernel 23.4.0, arm64, SIP enabled.
- Canonical blobs for alignment:
  - `book/examples/extract_sbs/build/profiles/airlock.sb.bin`
  - `book/examples/extract_sbs/build/profiles/bsd.sb.bin`
  - `book/examples/sb/build/sample.sb.bin`
- Current vocab artifacts (`validation/out/vocab/ops.json` / `filters.json`) are `status: partial` with decoder-derived op_count/op_table metadata only.

## Plan (summary)

1. Extract Sandbox-related binaries from the dyld shared cache.
2. Harvest operation/filter name tables from the extracted binaries.
3. Align harvested names with decoder op_count/op_table from canonical blobs; emit real vocab artifacts.
4. Rerun op-table alignment to fill operation IDs and record bucket↔ID relationships.

## Current status

- Experiment initialized; plan and notes created. Extraction/harvesting not yet performed.
- Dyld shared cache located at `/System/Volumes/Preboot/Cryptexes/OS/System/Library/dyld/dyld_shared_cache_arm64e`; extracted using a Swift shim that calls `/usr/lib/dsc_extractor.bundle` into `book/experiments/vocab-from-cache/extracted/`.
- Extracted artifacts include `usr/lib/libsandbox.1.dylib`, `usr/lib/system/libsystem_sandbox.dylib`, and `AppSandbox.framework` binary.
- Initial `strings -t x` on `libsandbox.1.dylib` reveals a contiguous block of ~190 operation-like names from `appleevent-send` through `default-message-filter`; needs alignment to the 167 `op_count` seen in canonical blobs before emitting vocab tables.
