# Notes — Field2 Atlas

- Initial scaffold created with seeds `0` (path), `5` (global-name), `7` (local); world fixed to `sonoma-14.4.1-23E224-arm64-dyld-2c0602c5`.
- Static/runtime/atlas outputs are currently placeholders keyed to existing mappings and golden traces; replace with regenerated data once `atlas_static.py` and `atlas_runtime.py` run.
- Keep runtime attempts, including `EPERM` / apply gates, recorded here with the command, profile, and seed field2 they target.
- Rebuilt atlas via `PYTHONPATH=. python book/experiments/field2-atlas/atlas_build.py` after refreshing `field2_inventory.json`/`unknown_nodes.json` (new UDP network variant + fcntl/right-name sweeps). Outputs remain stable (`runtime_backed` slice unchanged) but are aligned to the current anchor map/tag layouts.
