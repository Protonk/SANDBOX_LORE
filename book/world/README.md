# World Baselines

This directory holds per-host world baselines. Each world lives in its own subdirectory (for example `sonoma-14.4.1-23E224-arm64/`) with JSON files that captures the host identity, SIP state, pointers to the dyld manifest and other host-level knobs that influence decoding and runtime probes.

The `example-world/` directory is a template for creating a new world:

- `example-world/world-baseline.json` — fill in host fields, optional `world_id`, capture reason, and a pointer to the dyld manifest. Add runtime-impacting toggles such as `profile_format_variant`, `apply_gates`, and `tcc_state` as needed.
- `example-world/dyld-manifest.json` — list trimmed dyld slices (paths, byte sizes, SHA256 digests) and key symbol anchors used for vocab/encoder extraction. Hashing this manifest is the suggested way to derive `world_id`.

Treat `world-baseline.json` as immutable once published; regenerate downstream artifacts instead of editing an established baseline.
