# Tag switch triage (com.apple.security.sandbox, 14.4.1-23E224)

Purpose: keep a repeatable, stateless checklist for finding the PolicyGraph dispatcher/tag switch using the headless scaffold output (`switch_candidates.json` from `kernel_tag_switch.py`).

## How to run
- Use full analysis (do **not** pass `--no-analysis`) so functions/instructions exist.
- Command example (from repo root):  
  `python3 dumps/ghidra/scaffold.py kernel-tag-switch --java-home /Library/Java/JavaVirtualMachines/temurin-21.jdk/Contents/Home --exec`  
  (GHIDRA_HEADLESS env should point at `analyzeHeadless`; scaffold sets `HOME`/`GHIDRA_USER_HOME` to `dumps/ghidra/user/` and writes outputs to `dumps/ghidra/out/<build>/kernel-tag-switch/`.)

## Reading `switch_candidates.json`
- File: `dumps/ghidra/out/14.4.1-23E224/kernel-tag-switch/switch_candidates.json`
- Fields per candidate: `name`, `address`, `computed_jumps`, `jump_like`, `size`, `calling_convention`.
- Sorted by `computed_jumps` (desc), then `size` (desc).

## Triage workflow
1. **Filter**: start with highest `computed_jumps`; discard functions with very small `size` (toy jump tables).
2. **Shortlist**: grab the top ~20–30 entries with `computed_jumps >= 6` and `size` comfortably above a few hundred bytes.
3. **Inspect in Ghidra** (project: `dumps/ghidra/projects/sandbox_<build>`):
   - Look for a switch on a tag/field in the node struct, with multiple case arms.
   - Check for references to policy/node arrays, literal/regex tables, or op tables.
4. **Expand if needed**: if the dispatcher isn’t obvious in the top set, widen to the next 50–100 entries.

## Handy one-liner (outside Ghidra)
Print the top 20 candidates with size >= 500 bytes:
```sh
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("dumps/ghidra/out/14.4.1-23E224/kernel-tag-switch/switch_candidates.json")
d = json.loads(p.read_text())
cands = [c for c in d.get("candidates", []) if c["size"] >= 500]
cands.sort(key=lambda c: (c["computed_jumps"], c["size"]), reverse=True)
for c in cands[:20]:
    print(c)
PY
```

## Notes to encode in comments (in scripts)
- Tag-switch triage requires full analysis; `--no-analysis` will produce zero candidates.
- Output is a ranked heuristic list; manual inspection of the top entries in Ghidra is expected.
- Filtering by size and computed jump count trims noise before manual review.

## Current triage pass (quick filter)
- Source: `dumps/ghidra/out/14.4.1-23E224/kernel-tag-switch/switch_candidates.json` (full-analysis run).
- Counts: 7,926 total candidates; 900 with `size >= 500`; 9 with both `size >= 500` and `computed_jumps >= 6` (max jumps: 22).
- Shortlist (size >= 500, jumps >= 6), sorted by jump count then size:
  - `FUN_ffffff80005bbb90 @ 0x-7fffa44470` – jumps=22, size=6061
  - `FUN_ffffff8002377c16 @ 0x-7ffdc883ea` – jumps=9, size=3857
  - `FUN_ffffff8000546e60 @ 0x-7fffab91a0` – jumps=8, size=2529
  - `FUN_ffffff80006e9310 @ 0x-7fff916cf0` – jumps=6, size=10970
  - `FUN_ffffff80007f9150 @ 0x-7fff806eb0` – jumps=6, size=4184
  - `FUN_ffffff8002222324 @ 0x-7ffddddcdc` – jumps=6, size=3993
  - `FUN_ffffff80008641c0 @ 0x-7fff79be40` – jumps=6, size=3643
  - `FUN_ffffff80016a17ac @ 0x-7ffe95e854` – jumps=6, size=1359
  - `FUN_ffffff8000902bb0 @ 0x-7fff6fd450` – jumps=6, size=842
- Manual review order: walk the shortlist above in `dumps/ghidra/projects/sandbox_14.4.1-23E224` and look for a tag-based switch dispatching policy nodes. If none match, widen to size >= 500 with `computed_jumps >= 4` and pull the next 10–15 entries before looping back to Ghidra.
