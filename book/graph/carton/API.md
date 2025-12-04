# CARTON API surface

CARTON is the frozen web of IR and mappings for the Sonoma 14.4.1 host. Use it as the stable interface for textbook-grade facts instead of spelunking raw experiment outputs or validation scratch.

Public interface (guarded by the manifest at `book/graph/carton/CARTON.json`):
- `book/graph/mappings/vocab/{ops.json,filters.json}`
- `book/graph/mappings/runtime/runtime_signatures.json`
- `book/graph/mappings/system_profiles/digests.json`
- `book/graph/mappings/carton/operation_coverage.json`
- Helper module: `book/api/carton/carton_query.py` (public entrypoint; see `book/graph/carton/USAGE_examples.md`).

Plumbing (normally only needed when extending CARTON):
- Validation status + per-job IR under `book/graph/concepts/validation/out/…`.
- Promotion helpers under `book/graph/mappings/*/generate_*.py` and `run_promotion.py`.

Stability contract:
- Files listed in `CARTON.json` do not change except via a deliberate regeneration (validation driver → mapping generators → manifest update). Guardrail tests pin their hashes.
- Do not hand-edit CARTON JSON. Regenerate via the validation driver and mapping generators, then refresh the manifest.
- New experiments or mappings should live alongside CARTON; update the manifest only when you intentionally revise the frozen layer for Sonoma 14.4.1.
- Usage examples: `book/graph/carton/USAGE_examples.md` shows how to answer common questions via `book.api.carton.carton_query` and the coverage mapping without diving into raw JSON.
