# simbple Sonoma extraction (partial)

## Context
- Host baseline: `book/world/sonoma-14.4.1-23E224-arm64/world-baseline.json` (Apple Silicon, SIP enabled).
- Tool: `book/tools/sbpl/simbple` (build via `book/tools/sbpl/simbple/build`).
- Goal: evaluate a Sonoma system SBPL profile using container metadata.
- Container metadata input: `~/Library/Containers/com.apple.AppStore/.com.apple.containermanagerd.metadata.plist`.

## Symptom
- Initial runs crashed during `load-profile` (Signal 11/6) with unbound variables for new Sonoma ops/filters/modifiers and SBPL constructs (e.g., `system-fcntl`, `system-mac-syscall`, `mac-policy-name`, `telemetry`).
- Additional failures were triggered by imported profiles carrying `(version 3)` when the base profile uses `(version 1)`.
- Missing named arguments for `fcntl-command` and `fsctl-command` surfaced as unbound variables.

## Reproduction
```sh
SIMBPLE_TRACE=1 ./bin/simbple --platforms=catalina \
  -o /tmp/simbple-out.sb \
  ~/Library/Containers/com.apple.AppStore/.com.apple.containermanagerd.metadata.plist
```
After enforcing SBPL v1-only semantics in `book/tools/sbpl/simbple/src/scm/sbpl.scm`, the same command now crashes during `load-profile` (Signal 11) with trace output stopping at:
```
[trace] load-profile
```

Additional container metadata inputs tested without permissive mode:
```sh
SIMBPLE_TRACE=1 ./bin/simbple --platforms=catalina -o /tmp/simbple-archiveutility.sb \
  ~/Library/Containers/com.apple.archiveutility/.com.apple.containermanagerd.metadata.plist
SIMBPLE_TRACE=1 ./bin/simbple --platforms=catalina -o /tmp/simbple-facetime.sb \
  ~/Library/Containers/com.apple.FaceTime/.com.apple.containermanagerd.metadata.plist
SIMBPLE_TRACE=1 ./bin/simbple --platforms=catalina -o /tmp/simbple-ibooks.sb \
  ~/Library/Containers/com.apple.iBooks.BooksThumbnail/.com.apple.containermanagerd.metadata.plist
```
All three crash in the same place (`load-profile`, Signal 11).

## Interpretation
- Partial: the Catalina platform data and SBPL shim needed Sonoma-specific additions (new operations/filters/modifiers, version handling, and missing named args). With SBPL v1-only enforcement, loads now crash at `load-profile` for multiple container metadata inputs, suggesting the tool does not handle `error` paths safely (or the compiled profile format is now incompatible with the shim). This blocks further profile-level coverage.
- Partial: libsandbox string tables on this host provide values for `*ios-sandbox-system-container*`, `*ios-sandbox-system-group*`, and `*sandbox-executable-bundle*`, which have been applied. No string evidence yet for `*ios-sandbox-executable*`.

## Status
- blocked — enforcing SBPL v1-only semantics causes `simbple` to crash during `load-profile` for multiple container metadata inputs, so extraction cannot currently proceed without the v2/v3 compatibility shim; further SBPL coverage is blocked pending version-path error handling or profile decoding.

## Current Blockers
- The SBPL version shim is now v1-only (per maintainer direction), but version errors during `load-profile` currently lead to a crash (Signal 11) rather than a clean error path; this blocks progress on non-permissive extraction.
- `*ios-sandbox-executable*` remains a placeholder; no host string evidence found yet (substrate-only).
- Extraction has only been validated with the v2/v3 compatibility shim; under v1-only semantics, even baseline container metadata inputs crash before any rule output is produced.

## Pointers
- SBPL shim changes: `book/tools/sbpl/simbple/src/scm/sbpl.scm`, `book/tools/sbpl/simbple/src/scm/sbpl_v1.scm`.
- Platform data expansions: `book/tools/sbpl/simbple/src/platform_data/catalina/operations.c`, `book/tools/sbpl/simbple/src/platform_data/catalina/filters.c`.
- Modifier extensions: `book/tools/sbpl/simbple/src/sb/modifiers.c`.
- Trace/output examples: `/tmp/simbple-trace.log`, `/tmp/simbple-out.sb`.

## Artifact Evidence (partial)
- `book/graph/mappings/dyld-libs/usr/lib/libsandbox.1.dylib` string tables include:
  - `*ios-sandbox-system-container*` → `com.apple.sandbox.system-container`
  - `*ios-sandbox-system-group*` → `com.apple.sandbox.system-group`
  - `*sandbox-executable-bundle*` → `com.apple.sandbox.executable`
- No string evidence yet for `*ios-sandbox-executable*` in libsandbox (substrate-only).

## Log (append-only)
- 2024-12-03: extracted `fcntl-command` and `fsctl-command` named-argument values from `book/graph/mappings/dyld-libs/usr/lib/libsandbox.1.dylib` (world_id `sonoma-14.4.1-23E224-arm64-dyld-2c0602c5`) and replaced placeholders in `book/tools/sbpl/simbple/src/platform_data/catalina/filters.c` (`F_GETCONFINED`, `F_SETCONFINED`, and `APFSIOC_*` values).
- 2024-12-03: confirmed libsandbox contains `*ios-sandbox-container*` and `*ios-sandbox-application-group*` strings but no concrete values for `*ios-sandbox-system-container*`, `*ios-sandbox-system-group*`, or `*ios-sandbox-executable*`.
- 2024-12-03: removed the ad-hoc `iokit-user-client-class` filter entry from `book/tools/sbpl/simbple/src/platform_data/catalina/filters.c` to align with `book/graph/mappings/vocab/filters.json` (SBPL aliases it to `iokit-registry-entry-class`).
- 2024-12-03: rebuilt `simbple` and verified extraction succeeds without `SIMBPLE_PERMISSIVE=1` for `~/Library/Containers/com.apple.AppStore/.com.apple.containermanagerd.metadata.plist` (initial run hit a 10s timeout; rerun with a larger timeout completed).
- 2024-12-03: updated `book/tools/sbpl/simbple/src/scm/sbpl.scm` to enforce SBPL v1-only semantics; any `version` other than 1 now triggers an error.
- 2024-12-03: reran `simbple` without permissive mode against AppStore, Archive Utility, FaceTime, and iBooks container metadata; all crash at `load-profile` with Signal 11 after the v1-only change (`/tmp/simbple-*.log` capture traces that stop at `load-profile`).
- 2024-12-03: attempted a diagnostic run with `SIMBPLE_SKIP_PROFILE=1` (AppStore metadata) to isolate snippet loading; encountered unbound variables (`entitlement`, `when*`, `home-subpath`) and an assertion failure in `sbpl_create_rule` (Signal 6).
- 2024-12-03: searched `book/graph/mappings/dyld-libs/usr/lib/libsandbox.1.dylib` for `*ios-sandbox-*` values; found `com.apple.sandbox.system-container`, `com.apple.sandbox.system-group`, and `com.apple.sandbox.executable` strings (partial host evidence) and updated `book/tools/sbpl/simbple/src/scm/sbpl_v1.scm` accordingly. No `*ios-sandbox-executable*` string found.
