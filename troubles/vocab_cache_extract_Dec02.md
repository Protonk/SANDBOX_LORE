# Vocab Cache Extraction (Dec 02, 2025)

## Issue

We needed Sandbox’s Operation/Filter vocab tables (name ↔ ID) to unblock vocab mapping, but the usual binaries were not directly available:

- No `Sandbox.framework` or `libsandbox.dylib` in the expected filesystem locations.
- No `dyld_shared_cache_util` tool on this Sonoma system.

That left us stuck: the op/Filter vocab lives inside the dyld shared cache, but we didn’t yet know where the cache was or how to extract only the Sandbox slices using built-in tooling.

## Escalation

We escalated to a web‑enabled 5.1 chat model with a short description:

- Stated that Sandbox binaries were not visible on disk and `dyld_shared_cache_util` was missing.
- Asked for the correct dyld shared cache path on macOS 14 (arm64e) and a supported, built‑in way to extract Sandbox‑related binaries so we could scan them for vocab tables.

## Web model guidance (summary)

The web model’s answer had two key parts.

1. **Cache location on Sonoma / arm64e**

- Primary cache path:
  - `/System/Volumes/Preboot/Cryptexes/OS/System/Library/dyld/dyld_shared_cache_arm64e*`
- Possible compatibility copy:
  - `/System/Library/dyld/dyld_shared_cache_arm64e*`

This matched external descriptions of Ventura/Sonoma moving the active cache under the Cryptex Preboot volume.

2. **Extraction via `dsc_extractor.bundle`**

Because macOS no longer ships a standalone `dyld_shared_cache_util`, the model recommended using Apple’s `dsc_extractor.bundle`:

- Candidate bundle locations:
  - `/usr/lib/dsc_extractor.bundle`
  - `/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/usr/lib/dsc_extractor.bundle`
- Suggested a tiny Swift shim that:
  - `dlopen`s the bundle.
  - Looks up `dyld_shared_cache_extract_dylibs_progress`.
  - Calls it with:
    - the cache path,
    - an output directory,
    - an optional progress callback.

The sketch looked like:

```swift
import Foundation
import Darwin

typealias ExtractFn = @convention(c) (
  UnsafePointer<CChar>?,
  UnsafePointer<CChar>?,
  (@convention(block) (UInt32, UInt32) -> Void)?
) -> Int32

let args = CommandLine.arguments
guard args.count == 3 else {
  fputs("usage: extract_dsc <path-to-dyld_shared_cache> <output-dir>\n", stderr)
  exit(2)
}

let candidates = [
  "/usr/lib/dsc_extractor.bundle",
  "/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/usr/lib/dsc_extractor.bundle",
]

guard let bundlePath = candidates.first(where: { FileManager.default.fileExists(atPath: $0) }) else {
  fputs("dsc_extractor.bundle not found. Install Xcode if needed.\n", stderr)
  exit(1)
}

guard let handle = dlopen(bundlePath, RTLD_NOW) else {
  fputs("dlopen failed\n", stderr)
  exit(1)
}

defer { dlclose(handle) }

guard let sym = dlsym(handle, "dyld_shared_cache_extract_dylibs_progress") else {
  fputs("symbol not found in bundle\n", stderr)
  exit(1)
}

guard let fn = unsafeBitCast(sym, to: Optional<ExtractFn>.self) else {
  fputs("could not cast symbol\n", stderr)
  exit(1)
}

let rc = fn(args[1], args[2]) { cur, total in
  if total > 0 {
    fputs("\rExtracting \(cur)/\(total)", stderr)
  }
}
fputs("\n", stderr)
exit(rc == 0 ? 0 : rc)
```

The model then suggested running:

```bash
swiftc extract_dsc.swift -o extract_dsc
mkdir -p /tmp/dsc_out
./extract_dsc /System/Volumes/Preboot/Cryptexes/OS/System/Library/dyld/dyld_shared_cache_arm64e /tmp/dsc_out
```

and scanning the output tree for Sandbox components, e.g.:

```bash
find /tmp/dsc_out -type f \
  -path '*/PrivateFrameworks/Sandbox.framework/*' \
  -o -path '*/usr/lib/libsandbox*.dylib' \
  -o -path '*/usr/lib/libsystem_sandbox*.dylib'
```

## Resolution

We implemented a slightly adapted version of the guidance:

- Verified the cache at:
  - `/System/Volumes/Preboot/Cryptexes/OS/System/Library/dyld/dyld_shared_cache_arm64e`
  (no compat copy under `/System/Library/dyld` on this host).
- Confirmed `dsc_extractor.bundle` at `/usr/lib/dsc_extractor.bundle`.
- Added `book/experiments/vocab-from-cache/extract_dsc.swift` based on the suggested shim, adjusted the exit handling for our compiler, and built it with:
  - `xcrun swiftc extract_dsc.swift -module-cache-path .swift-module-cache -o extract_dsc`.
- Ran extraction into a project-local directory:

  ```bash
  mkdir -p book/experiments/vocab-from-cache/extracted
  book/experiments/vocab-from-cache/extract_dsc \
    /System/Volumes/Preboot/Cryptexes/OS/System/Library/dyld/dyld_shared_cache_arm64e \
    book/experiments/vocab-from-cache/extracted
  ```

- Confirmed that the extracted tree now includes:
  - `usr/lib/libsandbox.1.dylib`
  - `usr/lib/system/libsystem_sandbox.dylib`
  - `System/Library/PrivateFrameworks/AppSandbox.framework/Versions/A/AppSandbox`

Immediate next step (tracked in the vocab-from-cache experiment, not here) is to:

- Parse `libsandbox.1.dylib` to recover the ordered Operation name block (~190 operation-like strings from `appleevent-send` through `default-message-filter`).
- Align that block with the decoder’s `op_count=167` from canonical blobs so we can assign stable Operation IDs and emit real `ops.json` / `filters.json` for this host.
