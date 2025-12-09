# Notes

- Re-ran `python run_adversarial.py` after adding file-write* rules to structural/path_edges SBPL and adding a network-outbound family (`net_outbound_allow`, `net_outbound_deny`).
  - Filesystem/mach families remain as before: struct_flat vs struct_nested match on read/write; path_edges shows `/tmp`→`/private/tmp` EPERM mismatches; mach literal/regex variants match.
  - Network: initial ping/TCP attempts mismatched on allow due to client startup constraints. Swapped the client to `/usr/bin/nc` (no Python in the sandbox) with explicit startup shims; TCP loopback now succeeds in allow profile and denies in deny profile.
