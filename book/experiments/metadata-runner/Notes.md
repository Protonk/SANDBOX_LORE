# Notes

- `file-write-metadata` is not in the SBPL vocabulary; metadata writes are exercised via `file-write*` using `chmod` in the runner.
- Swift runner (`metadata_runner.swift`) uses `sandbox_init` with SBPL input and issues `lstat`/`getattrlist`/`setattrlist`/`fstat` (read-metadata) and `chmod`/`utimes`/`fchmod`/`futimes`/`lchown`/`fchown`/`fchownat`/`lutimes` (metadata write proxies), emitting JSON.
- `run_metadata.py` compiles SBPL probes, builds the runner, seeds fixtures via canonical paths, and runs the matrix across alias/canonical paths for both operations and all syscalls; outputs land in `out/runtime_results.json` and `out/decode_profiles.json`.
- Expanded syscall runs show the same pattern across all tested syscalls and anchor forms (literal, subpath, regex): canonical-only/both allow canonical requests; alias-only deny all; both-path profiles still deny alias requests. Alias anchors do not grant metadata access, unlike the data read/write canonicalization experiment. `setattrlist` returned `EINVAL` on canonical paths and `EPERM` on aliases.
- Control sanity: `(allow default)` profile via the runner permits metadata operations, confirming the runner is behaving; targeted allows are what surface the alias/canonical divergence.
