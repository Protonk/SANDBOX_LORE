# Agents in `book/graph/Sources/`

Purpose: Swift generator/validator that reads concept markdown + mapping manifests and emits JSON artifacts and a validation report.

Run: `swift run` from `book/graph/`.

Modify:
- Add Swift types/validators for new schema slices (e.g., mapping manifests) in `main.swift` (or split into additional source files if it grows).
- Keep validation non-fatal: emit reports to `book/graph/validation/validation_report.json`.

Do not:
- Hard-code paths outside `book/graph/`; keep inputs relative and documented in `book/graph/README.md`.
