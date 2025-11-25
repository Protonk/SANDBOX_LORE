# TextEdit sandbox specialization

This directory now holds the scaffolding for “Chapter 2: TextEdit’s Sandbox Profile” plus the specialized profile artifacts.

## Chapter 2 scaffolding

All `tools/02.x_*` scripts are scaffolds meant to keep the wiring runnable; the `notes/` files capture the plan so future authors can pick up the work mid-stream.

### 2.1 What TextEdit is allowed to do

- `tools/02.1_capability_survey.py` — loads `textedit-entitlements.plist` and `textedit-specialized.sb` and will eventually emit a summary of visible capabilities (printing, user-selected files, ubiquity, etc.).
- `notes/02.1-capability-survey.md` — planning notes and intended outputs for Section 2.1.

### 2.2 Profiles, containers, and entitlements in practice

- `tools/02.2_profiles_and_containers.py` — wiring for correlating profile, entitlements, and container roots.
- `notes/02.2-profiles-containers-entitlements.md` — outline of how these will be explained in the chapter.

### 2.3 Tracing real operations through the sandbox

- `tools/02.3_trace_operations.sh` — tracing stub for mapping UI actions to syscalls and, later, to SBPL rules.
- `notes/02.3-tracing-real-operations.md` — scenarios and trace/analysis plan.

### 2.4 What TextEdit shows us about the broader system

- `tools/02.4_pattern_extraction.py` — stubs for extracting and classifying structural patterns from `textedit-specialized.sb`.
- `notes/02.4-broader-system-lessons.md` — notes on general lessons (patterns, limitations, global policy).

## Profile source notes

- `textedit-specialized.sb` is a pedagogical specialization of `profiles/textedit/application.sb` using the checked-in TextEdit entitlements and container notes.
- Parameters are fixed conceptually to `application_bundle_id = "com.apple.TextEdit"` and `application_container_id = "com.apple.TextEdit"`; paths remain parameterized for portability.
- Entitlement guards (`when`/`if`/`unless`) were evaluated: TextEdit’s entitlements inline the active bodies (e.g., printing, user-selected file access) and drop the inactive ones with short comments.
- Array entitlements were expanded: the ubiquity container list produces rules for `com.apple.TextEdit`; all other entitlement arrays were omitted because TextEdit has no values for them.
- Param-guarded forms are assumed true for TextEdit and kept as-is with small “Active” comments rather than substituting concrete system paths.
- The result is meant for documentation, not a bit-for-bit clone of the live sandbox blob.
