# AGENTS — `dumps/`

This directory holds reverse-engineering artifacts and plans for the current macOS build. Treat it as the place to read from, not a staging area for tracked outputs.

- `RE_Plan.md` — entry point for the 14.4.1-23E224 extraction effort; outlines kernel/userland/profile goals and desired data products.
- `Sandbox-private/14.4.1-23E224/` — git-ignored host artifacts:
  - `kernel/BootKernelExtensions.kc` — contains `com.apple.security.sandbox` (PolicyGraph layout, op table, filter dispatch).
  - `userland/libsystem_sandbox.dylib` — compiler/loader surfaces, op/filter vocab tables.
  - `profiles/Profiles/*.sb` and `profiles/compiled/` — SBPL templates and compiled blobs (e.g., TextEdit).
  - `meta/SYSTEM_VERSION.txt` — provenance for the extracted set.

Warnings and handling:
- Do **not** move or copy anything from `Sandbox-private/` into tracked directories (`book/`, `substrate/`, or anywhere else in the repo). Work in place and keep derivatives inside `dumps/` (prefer git-ignored paths) to avoid leaking host data into version control.
- Align vocabulary and interpretation with `substrate/` (Orientation/Concepts/Appendix/Environment/State) when writing notes or scripts against these blobs.
