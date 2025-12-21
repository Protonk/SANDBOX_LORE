# SBPL corpus

This is a curated, host-bound SBPL specimen set for the Sonoma 14.4.1 baseline
(`world_id sonoma-14.4.1-23E224-arm64-dyld-2c0602c5`). It exists to keep known
inputs in one place and to make provenance + hashes explicit.

## Families

- `baseline/`
  - Minimal compile and shape sanity profiles (allow/deny + tiny examples).
- `golden-triple/`
  - The golden-triple specimen set used by file-read bucket experiments.
- `network-matrix/`
  - The libsandbox-encoder network matrix used to witness domain/type/proto
    emission, including order-variant and numeric-proto specimens.
- `gate-witness/`
  - Minimal failing/passing neighbors for known apply-gated shapes (from the
    gate-witness experiment).

## Population and manifest

`SOURCES.json` is the curated list of provenance entries (repo-relative source
paths). Run the sync tool to copy sources into this corpus and to refresh the
manifest:

```sh
python3 book/tools/sbpl/sync_corpus.py
```

This writes `MANIFEST.json` with hashes for both source and corpus copies.

## Reuse

- New experiments should pull inputs from this corpus instead of re-embedding
  specimen SBPL in experiment-local directories.
- Use `book/tools/preflight/preflight.py` to classify corpus entries for
  apply-gate avoidance.
- Use `book/api/profile_tools` to compile, decode, or diff these inputs.
