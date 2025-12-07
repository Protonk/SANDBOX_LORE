# CARTON API surface

The CARTON API (`book.api.carton.carton_query`) is the public entrypoint for querying CARTON. It answers questions about operations, system profiles/profile layers, filters, and runtime signatures using the CARTON manifest at `book/api/carton/CARTON.json` and its listed mappings.

For CARTON’s role in the project and how concepts map to artifacts, see `README.md`. For agent‑level routing guidance, see `AGENTS.md`.

All loads go through `CARTON.json`: `carton_query` resolves logical names to paths via the manifest, recomputes SHA‑256 hashes when a manifest hash is present, and validates basic schema before returning data.

## Discovery helpers

These functions expose what CARTON knows without requiring callers to know internal file layouts.

- `list_operations() -> List[str]`
  - Returns a sorted list of operation names that CARTON knows about.
  - Backed by `carton.operation_index.json` and the operation vocabulary.
- `list_profiles() -> List[str]`
  - Returns a sorted list of system profile/profile‑layer identifiers known to CARTON.
  - Backed by `carton.profile_layer_index.json` and system profile digests.
- `list_filters() -> List[str]`
  - Returns a sorted list of filter names from the CARTON filter index.
  - Backed by `carton.filter_index.json` and the filter vocabulary.
- `ops_with_low_coverage(threshold: int = 0) -> List[Dict[str, object]]`
  - Returns operations whose combined system‑profile and runtime‑signature counts are less than or equal to `threshold`.
  - Each entry contains: `name`, `op_id`, and a `counts` dict with `system_profiles` and `runtime_signatures`.
  - Backed by `carton.operation_coverage.json`.
- `list_carton_paths() -> Dict[str, str]`
  - Returns resolved filesystem paths for the core CARTON mappings (vocab, runtime signatures, system profile digests, coverage, indices).
  - Intended for diagnostics and debugging, not for regular querying.

## Operation‑centred helpers

These helpers answer “what do we know about operation X?” type questions. All expect a CARTON‑known operation name and will raise `UnknownOperationError` on unknown names.

- `profiles_with_operation(op_name: str) -> List[str]`
  - Returns a list of system profile identifiers that include the given operation in their op‑table.
  - Backed primarily by `carton.operation_coverage.json`, with a fallback to system profile digests if coverage lacks explicit system profile entries.
- `profiles_and_signatures_for_operation(op_name: str) -> Dict[str, object]`
  - Returns a compact mapping for the operation:
    - `op_name`: the name passed in.
    - `op_id`: numeric operation ID.
    - `system_profiles`: list of system profiles that include this operation.
    - `runtime_signatures`: list of runtime signature IDs that probe this operation.
    - `counts`: `{"system_profiles": int, "runtime_signatures": int}`.
    - `known`: `True` for operations present in the CARTON vocab.
  - Backed by the operation vocab and coverage mapping.
- `operation_story(op_name: str) -> Dict[str, object]`
  - Returns a concept‑shaped “story” for the operation:
    - `op_name`, `op_id`, `known`,
    - `system_profiles`: as above,
    - `profile_layers`: today a simple list (for example, `["system"]` when system profiles exist),
    - `runtime_signatures`: IDs of signatures that probe this operation,
    - `coverage_counts`: same counts as `profiles_and_signatures_for_operation`.
  - Intended as the primary helper when an agent wants a single, joined view of how an operation shows up in system profiles and runtime.

## Profile / profile‑layer helpers

- `profile_story(profile_id: str) -> Dict[str, object]`
  - Returns a concept‑shaped view of a system profile/profile layer:
    - `profile_id`: identifier from system profile digests.
    - `layer`: a simple label such as `"system"` for current profiles.
    - `ops`: list of `{"name": op_name, "id": op_id}` entries for operations present in the profile’s op‑table and vocab.
    - `runtime_signatures`: sorted list of runtime signature IDs that touch any of those operations, derived from coverage.
    - `filters`: a placeholder block, currently `{"known": False, "filters": []}` to avoid guessing filter linkage before it is mapped.
  - Raises `CartonDataError` if the profile ID is not present in system profile digests or if required CARTON mappings are missing or malformed.

## Filter helpers

- `filter_story(filter_name: str) -> Dict[str, object]`
  - Returns information about a filter known to CARTON:
    - `filter_name`: the name passed in.
    - `filter_id`: numeric filter ID from the vocab, if present.
    - `known`: boolean flag indicating whether CARTON considers this filter concretely mapped.
    - `usage_status`: one of `present-in-vocab-only`, `referenced-in-profiles`, `referenced-in-runtime`, or `unknown`.
    - `system_profiles`: list of system profiles where this filter is known to appear (may be empty for now).
    - `runtime_signatures`: list of runtime signatures where this filter is known to appear (may be empty for now).
  - Backed by `carton.filter_index.json`. Raises `CartonDataError` if the filter name is not in the index or the index is malformed.

## Runtime‑signature helpers

- `runtime_signature_info(sig_id: str) -> Dict[str, object]`
  - Returns a view of a runtime signature:
    - `probes`: the recorded probe outcomes for this signature, taken from `runtime_signatures.json`.
    - `runtime_profile`: the runtime profile/blob associated with this signature, if recorded in `profiles_metadata`.
    - `expected`: any expected outcome entry from the runtime “expected matrix”, when present.
  - Does not currently raise a dedicated error for unknown IDs; absent entries will simply appear as `None`. Use this helper as a read‑only view into known signatures.

## Error types and manifest behavior

- `CartonDataError`
  - Raised when CARTON data is missing, malformed, or out of sync with the manifest (for example: missing file, JSON decode failure, required top‑level keys absent, SHA‑256 hash mismatch, or manifest drift).
  - Signals that the local CARTON surface is not trustworthy; callers should not attempt to work around this and should instead rerun the validation/promotion pipeline.
- `UnknownOperationError`
  - Raised when a helper that expects a known operation name (for example, `operation_story` or `profiles_and_signatures_for_operation`) cannot find it in the CARTON vocab.
  - Signals that the concept is unknown to CARTON on this host (typo, different host, or out‑of‑date CARTON), not that the data layer is corrupted.

## Small examples

These snippets illustrate typical use; they all assume `from book.api.carton import carton_query`.

- Discover and inspect an operation:
  - `ops = carton_query.list_operations()`
  - `story = carton_query.operation_story("file-read*")`
- Find profiles that exercise an operation:
  - `profiles = carton_query.profiles_with_operation("file-read*")`
- Inspect a profile:
  - `story = carton_query.profile_story("sys:bsd")`
- Inspect a runtime signature:
  - `info = carton_query.runtime_signature_info("bucket4:v1_read")`
- Explore under‑covered operations:
  - `low = carton_query.ops_with_low_coverage(threshold=0)`

Callers should be prepared to catch `UnknownOperationError` when probing for operations that may not exist, and `CartonDataError` when the local CARTON state is out of date or damaged.
