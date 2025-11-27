

## Narrative: extensions as a third dimension in practice

This probe is our first hands-on look at sandbox extensions as the “third dimension” of Seatbelt policy: runtime tokens that sit alongside platform profiles and per-process profiles in the Seatbelt label and flip `(extension ...)` filters in the `file-read*` / `file-write*` PolicyGraphs from false to true. The demo program (`extensions_demo.c`) is deliberately simple: it performs a baseline `open()` on a target path, then calls into `libsandbox` to issue a `com.apple.app-sandbox.read` extension for that path, consumes the token into its Seatbelt label, and retries the `open()`. Conceptually, the sequence is: “no extensions → extension issuance attempt → extension attached to the label → re-evaluation of the same operation with an extra dynamic capability present.”

What we actually observe on this macOS 14.4.1 host is a story dominated not by the sandbox graphs, but by the extension API’s behavior for unentitled callers and by a bug in the original demo binary. First, the prebuilt `HEAD` artifact crashes with `Sandbox(Signal 11)`. The crash report shows `sandbox_extension_consume` calling `_platform_strcmp` with a NULL pointer (`x0=0`), and disassembly of that binary confirms there is no guard on `token == NULL`: as soon as `sandbox_extension_issue_file` returns `rc==0`, the code jumps to `sandbox_extension_consume` and hands it whatever is in the token slot. On this host, `libsandbox` is returning “success” (`rc=0`) but no token (`token=NULL`) and setting `errno=EPERM` for both a strongly protected path (`/private/var/db/ConfigurationProfiles`) and a permissive path (`/tmp`). In other words, the issuance gate is rejecting our caller, but the API surface signals that rejection via “success with NULL token” rather than a non-zero return code. The combination of that API quirk and the missing NULL check in the demo produces the crash.

Once we rebuild the demo from source—with an explicit guard that treats “`rc!=0` or `token==NULL`” as failure—the picture becomes much clearer. The rebuilt binary no longer crashes; instead, we see:

- A baseline `open()` on `/private/var/db/ConfigurationProfiles` that succeeds outright on this host, demonstrating that the current Seatbelt label plus SIP/TCC state already allow this read for our unsandboxed CLI.
- An extension issuance attempt that reports `rc=0, token=NULL, errno=EPERM`, which we interpret as “no extension granted for this caller,” consistent with the substrate’s claim that issuing extensions typically requires specific entitlements and trusted callers.
- The guarded path in the demo skipping `sandbox_extension_consume` and `sandbox_extension_release` entirely when no token is present, and exiting with an explanatory message instead of attempting to widen its label.

From the substrate’s perspective, this is a useful example of how extensions interact with the rest of the policy stack, even though we never see a successful extension in flight. Extensions are modeled as dynamic capabilities attached to the Seatbelt label and referenced by `(extension ...)` filters in the PolicyGraph. On this host, the label for our test process has no such tokens, and the issuance path is blocked at the `libsandbox` API/entitlement layer, so any branch of the graph that depends on `(extension ...)` being true remains inaccessible. The baseline `open()` succeeds because the effective policy stack—platform profile, any per-process profile (in this case, essentially none), containers (not relevant here), and SIP/TCC—is already permissive for this path. The failed issuance then tells us that “successful extension-driven widening” is restricted to processes with the appropriate entitlements or launch context, and that unentitled ad-hoc binaries can’t simply mint tokens to bypass path rules.

For our empirical project, the key lesson is similar to the mach-services probe: you cannot study extensions in isolation. The behavior we see is the conjunction of (1) the static sandbox policy for the process, (2) the extension issuance rules enforced by `libsandbox` based on entitlements and compiled profile source, and (3) adjacent controls like SIP/TCC that may already allow or deny the underlying filesystem operation. Here, the extension path is blocked before the sandbox graphs ever see a non-empty token set, but the traces still reinforce the core substrate story: extensions are a narrow, capability-like overlay tied to specific callers and entitlements, not a generic “escape hatch” any binary can exercise at will.

## Summary so far

- Two binaries exist: the prebuilt `HEAD` artifact (`/tmp/extensions_demo.head`) still crashes with `Sandbox(Signal 11)`; a fresh rebuild from source runs and exits cleanly after seeing `token=NULL`.
- Crash log `extensions_demo-2025-11-26-202649.ips` shows `sandbox_extension_consume` calling `_platform_strcmp` with `x0=0`, i.e., a NULL token path; this matches the behavior seen when libsandbox returns `rc=0, token=NULL`.
- Disassembly confirms the crashing binary lacks a guard on `token == NULL`; it proceeds to consume unconditionally when `rc==0`. The rebuilt binary includes the guard and skips consume/release when `token` is NULL.
- libsandbox on this host (macOS 14.4.1, SIP enabled) returns `rc=0, token=NULL, errno=EPERM` for `sandbox_extension_issue_file("com.apple.app-sandbox.read", "/private/var/db/ConfigurationProfiles", 0, &token)` and also for `/tmp`. This matches prior ctypes notes and explains the NULL deref.
- Baseline `open()` to `/private/var/db/ConfigurationProfiles` succeeds here, so the demo does not illustrate a denial→allow transition even when the crash is avoided.

## Reproduction notes

- `./book/examples/extensions-dynamic/extensions_demo` (prebuilt from `HEAD`):
  - Crash: `Sandbox(Signal(11))`.
  - Crash log excerpt: `EXC_BAD_ACCESS (SIGSEGV) KERN_INVALID_ADDRESS at 0x0`, faulting in `_platform_strcmp` invoked from `sandbox_extension_consume` → `main`.
  - `usedImages`: `libsystem_sandbox.dylib` is the caller; SIP enabled; macOS 14.4.1 (23E224).
- `clang book/examples/extensions-dynamic/extensions_demo.c -o book/examples/extensions-dynamic/extensions_demo -ldl` (fresh build):
  - Run output:
    - `open("/private/var/db/ConfigurationProfiles") -> success (fd=3)`
    - `sandbox_extension_issue_file failed rc=0 errno=1 (Operation not permitted)`
    - Skips consume/release; exits normally.

## Root cause hypothesis

- The crash stems from calling `sandbox_extension_consume` with a NULL token. The prebuilt binary was compiled before the null-token guard landed (or with different optimization/layout that elided the guard).
- libsandbox returns “success” (rc=0) but no token for unentitled callers, so any code path that treats `rc==0` as sufficient will dereference NULL inside `sandbox_extension_consume`.

## Suggested fixes/documentation for this probe

- Always rebuild before running (or remove the prebuilt binary from version control) to ensure the null-token guard is present.
- Treat both `rc!=0` and `token==NULL` as hard failure; skip consume/release in that case.
- Capture the current behavior as expected for unentitled callers: `rc=0, token=NULL, errno=EPERM`.
- If we want a denial→allow demonstration, wrap the demo in a sandbox profile that denies the target path or pick a path that the current label cannot open; otherwise the baseline `open` succeeds.
- If deeper debugging of libsandbox behavior is needed, it likely requires entitlements or SIP-off tracing; alternatively, mock token issuance to illustrate the API without touching libsandbox.

## Detailed trace log

- `./book/examples/extensions-dynamic/extensions_demo` → `Sandbox(Signal(11))`.
- `lldb -- ./book/examples/extensions-dynamic/extensions_demo` could not attach (process exits before stop).
- `clang book/examples/extensions-dynamic/extensions_demo.c -o book/examples/extensions-dynamic/extensions_demo -ldl` then rerun → no crash; sees `rc=0, token=NULL, errno=1`.
- `git show HEAD:book/examples/extensions-dynamic/extensions_demo > /tmp/extensions_demo.head; chmod +x` → `/tmp/extensions_demo.head` crashes with `Sandbox(Signal(11))`.
- Crash log `extensions_demo-2025-11-26-202649.ips`:
  - Exception: `EXC_BAD_ACCESS (SIGSEGV) KERN_INVALID_ADDRESS 0x0`
  - Faulting frame: `_platform_strcmp` called from `sandbox_extension_consume`
  - Register state shows `x8` (consume fn) and `x0=0`, consistent with NULL token deref.
- SHA256 diff: prebuilt `HEAD` binary `47acae…f8` vs rebuilt `41910c…e7a`.
- Disassembly:
  - Prebuilt (`/tmp/extensions_demo.head`): on `rc==0` branch, immediately calls `sandbox_extension_consume` without checking `token`.
  - Rebuilt (`book/examples/extensions-dynamic/extensions_demo`): includes `token == NULL` check; skips consume when NULL.
- libsandbox location:
  - `nm` on `/usr/lib/libsandbox.dylib` fails (path not present); symbols resolved at runtime via `dlsym` against `libsystem_sandbox.dylib` from the shared cache (`usedImages` in crash log).
