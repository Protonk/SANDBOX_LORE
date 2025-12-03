# Field2 hunting

This note tracks the ongoing attempt to understand the third 16‑bit payload field in PolicyGraph nodes on this Sonoma host. Earlier notes called this slot `field2`; in the decoder and experiments we now surface it as `filter_arg_raw`. It collects the paths we have already taken, what static and kernel evidence we have in hand, and a short list of next steps that still look worth pursuing.

The goal is **not** to guess semantics for the remaining “high” values, but to keep a grounded record of where the unknowns live, which tools and experiments now exist around them, and what work would actually move them from “mystery constant” toward a validated mapping.

## Local definition and scope

- In this project, `field2` is the third 16‑bit payload in a node record for graph‑based profiles. In the decoder and inventories it is exposed as:
  - `filter_arg_raw` – the stored u16 from the node.
  - `field2_hi = filter_arg_raw & 0xc000`
  - `field2_lo = filter_arg_raw & 0x3fff`
- For **low** values, `filter_arg_raw` lines up directly with the filter vocabulary on this host (e.g. 0=path, 1=mount-relative-path, 3=file-mode, 5=global-name, 6=local-name, 7=local, 8=remote, 11=socket-type, 17/18 iokit-*, 26/27 right-name/preference-domain, 80=mac-policy-name).
- This note is about the **exceptions**: high or structurally odd `filter_arg_raw` values that do not map to any known filter ID, literal index, or obvious table offset, and that show up only in richer platform profiles or specific mixed probes.

All of the concrete data for this note now lives under `book/experiments/field2-filters/`:

- `out/field2_inventory.json` – per‑profile histograms, hi/lo splits, tag counts, op reach.
- `out/unknown_nodes.json` – per‑profile list of “unknown” nodes (no vocab hit or non‑zero hi bits) with tag, fan‑in/fan‑out, literals, and op reach.
- Scripts: `harvest_field2.py`, `unknown_focus.py`, and arm64e helper/evaluator dumps under `dumps/ghidra/out/14.4.1-23E224/find-field2-evaluator/`.

## Static evidence on this host

### Canonical profiles (`bsd`, `airlock`, `sample`)

From `book/examples/extract_sbs/build/profiles/{bsd,airlock,sample}.sb.bin`, harvested via `harvest_field2.py`:

- **`bsd.sb.bin`**
  - Node count ~41.
  - `filter_arg_raw` values include:
    - Low IDs with direct vocab matches: 0, 1, 3, 5, 6, 7, 8, 11, 17, 18, 26, 27, 80.
    - High / unknowns: `170`, `174`, `115`, `109` (all with `field2_hi=0`, on tag 26), and `16660` (on tag 0 with `field2_hi=0x4000`, `field2_lo=0x0114`).
  - `unknown_focus.py` shows:
    - `16660` lives on tag 0 as a shared tail: `fan_in ≫ 1`, `fan_out = 1`, reachable from op IDs 0–27 (the default/file* cluster).
    - The other high values (170/174/115/109) sit on tag 26, have `fan_out=1`, `fan_in=0`, and no op reach in the current decoding.

- **`airlock.sb.bin`**
  - Very small graph (node count ~7).
  - `filter_arg_raw` is dominated by three unknown values: `165`, `166`, and `10752` (all with `field2_hi=0`).
  - `unknown_focus.py` shows:
    - These nodes mostly sit on tags 166 and 1, with 10752 on tag 0.
    - Their op reach is concentrated on a single operation ID, 162 (`system-fcntl` in the current operation vocabulary).
    - Some are self‑loops or have only invalid/out‑of‑bounds successors.

- **`sample.sb.bin`**
  - Node count ~32.
  - `filter_arg_raw` mostly low and well‑behaved: {0,1,3,7,8} with clear path/socket matches.
  - A single sentinel, `3584` (`field2_hi=0`, `field2_lo=0x0e00`), appears on tag 0, op‑empty, and is marked as unknown.

### Flow‑divert and mixed‑network probes

Across network‑focused profiles (from `probe-op-structure` and local SBPL in `book/experiments/field2-filters/sb/`), we see:

- Simple, single‑filter probes (socket-domain/type/protocol, subpath/literal on file operations, vnode‑type, etc.) **collapse** to generic path/name/socket IDs: `filter_arg_raw` in {0,1,3,4,5,6,7,8,11}. These shapes are dominated by shared scaffolding; the intended filter often does not surface as a distinct ID.
- Richer, mixed profiles do surface one repeatable unknown tied to flow‑divert:
  - In `v4_network_socket_require_all`, `v7_file_network_combo`, and `net_require_all_domain_type_proto`, nodes referencing the literal `com.apple.flow-divert` carry:
    - A triple `{7, 2560, 2}` across nodes (local + unknown + xattr-style IDs),
    - A specific unknown `filter_arg_raw = 2560` (`field2_hi=0`, `field2_lo=0x0a00`) on tag 0, with both successor edges pointing at node 0 (structurally a trivial branch).
  - Inventories and `unknown_focus.py` agree:
    - This 2560 node appears only when **socket domain, type, and protocol are all required together** (require-all); any two of the three reduce the profile back to low IDs and the 2560 node disappears.
    - In all current decodes, the 2560 node is op‑empty (no operation entrypoint lands there directly), and its fan‑in=0, fan‑out=2 (both edges = 0).
- Attempts to isolate the flow‑divert behavior into small, “clean” SBPL profiles (network‑only, or network + mach‑lookup) consistently collapse back to low IDs; the 2560 value has so far remained confined to the original mixed probes.

### Focused synthetic probes

Several synthetic SBPL profiles were designed to “peel out” the bsd/airlock high values into simpler graphs:

- `dtracehelper_posixspawn.sb` and `bsd_tail_context.sb`:
  - Use only a few literals (`/dev/dtracehelper`, `/usr/share/posix_spawn_filtering_rules`) and simple allow/deny around file operations and mach‑lookup.
  - Decode to graphs with only low path/socket IDs (plus the 3584 sentinel); none of the high bsd values (170/174/115/109/16660) appear.

- `bsd_ops_default_file.sb`:
  - Targets ops 0,10,21–27 with simple path literals.
  - Again, only low IDs and the 3584 sentinel appear; the bsd high values remain unique to the full `bsd.sb.bin`.

- `airlock_system_fcntl.sb`:
  - Focuses on op 162 (`system-fcntl`) with `fcntl-command` filters.
  - Produces mostly low path/socket IDs but also a **new sentinel**:
    - `filter_arg_raw = 0xffff` (`field2_hi=0xc000`, `field2_lo=0x3fff`) on tag 1, op‑empty, with no attached literals.
  - This sentinel does not appear in the canonical `airlock` blob, but it shows up as another “high” value in the same conceptual area (system‑fcntls).

Across all of these, the pattern is consistent with what we saw early on: most of the graph uses the public filter vocabulary in a straightforward way, while a small set of regions (bsd tail, airlock system‑fcntls, flow‑divert mixed graphs) rely on `filter_arg_raw` values that we cannot yet interpret.

## Kernel‑side evidence (arm64e sandbox kext)

The field2‑filters experiment now includes a concrete look at how the kernel consumes the third node slot on this host, using the extracted arm64e sandbox kext:

- The sandbox binary (`com.apple.security.sandbox`) was carved out of the BootKC fileset and disassembled; helper search is captured under:
  - `dumps/ghidra/out/14.4.1-23E224/find-field2-evaluator/`.
- A small helper, identified as `__read16` at `fffffe000b40fa1c`, is the canonical u16 reader:
  - It bounds‑checks the profile buffer and then issues a plain `ldrh/strh` on the payload.
  - There are **no masks, bit‑tests, or shifts** applied to the u16 in this helper.
- The main evaluator `_eval` at `fffffe000b40d698`:
  - Uses masks like `0x7f`, `0xffffff`, and `0x7fffff` for other payload fields and indices.
  - Contains **no `0x3fff`/`0x4000` masks or similar bit slicing on the value returned by `__read16`**.
- Earlier automated scans for immediates (`0x3fff`, `0x4000`, `0xc000`, `0xa00`, `0x2a00`, `0x4114`) across the kernel cache and in the sandbox slice turned up no obvious bit‑field operations on `filter_arg_raw`.

Taken together, the current kernel evidence on this host supports a narrow but important claim:

- The kernel **reads `filter_arg_raw` as a plain 16‑bit value and forwards it to higher‑level logic unmasked**. The hi/lo split we use in the experiment (`field2_hi`, `field2_lo`) is an analytic view for humans and tools, not a structure the kernel itself enforces at the load point.
- Any special semantics for high values (like bsd’s 16660 or airlock’s 10752/0xffff) must therefore arise either:
  - in comparison code that looks at the raw u16 (e.g., equality/inequality against specific constants), or
  - from code that uses `filter_arg_raw` as an index into auxiliary tables (whose contents we haven’t tied back yet),
  and not from a generic “split hi/lo” bitfield at the reader.

We do **not** yet have a confirmed call site that ties a specific unknown constant (2560, 16660, 10752, 0xffff, 3584) to a particular branch or helper; that remains open.

## Paths taken so far

The work to date breaks down into three main clusters:

1. **System‑profile census and vocab alignment**
   - Confirmed that low `filter_arg_raw` values in `bsd` and `sample` map cleanly to `filters.json` on this host.
   - Identified all “unknown” values and their tag/op context via `field2_inventory.json` and `unknown_nodes.json`, with:
     - bsd tail 16660 on tag 0, ops 0–27;
     - bsd 170/174/115/109 on tag 26, op‑empty;
     - airlock 165/166/10752 on tags 166/1/0, op 162;
     - sample 3584 on tag 0, op‑empty.

2. **SBPL probes (single‑filter and mixed)**
   - Single‑filter probes (for basic path/dir/socket/iokit filters) mostly reproduce generic path/name IDs and occasionally simple sentinels; they do **not** surface the high system‑profile values.
   - Mixed network probes did surface the 2560 value tied to `com.apple.flow-divert`, but only under a precise require‑all conjunction for domain + type + protocol; attempts to simplify these profiles stripped away 2560 and left only low IDs.
   - Focused bsd/airlock clones (dtracehelper/posix_spawn, default/file ops, system‑fcntls) have so far:
     - failed to replicate bsd’s high values outside the canonical blob;
     - created one new sentinel (0xffff) in a synthetic airlock‑style profile.

3. **Kernel displacement and helper search**
   - Carved and disassembled the arm64e sandbox kext; identified a u16 reader (`__read16`) used by `_eval` and related helpers.
   - Verified that `filter_arg_raw` is loaded and passed around as a raw u16 at the helper/evaluator level (no hi/lo bitfield splitting here).
   - Ran targeted mask/imm searches for the most interesting constants (16660/2560/10752/0xffff/3584) and common “mask patterns” (0x3fff/0x4000/0xc000) without finding a clean bitfield scheme or constant compare in the evaluator path.

At this point, further SBPL‑only probing looks like diminishing returns: synthetic profiles keep collapsing into low IDs or generating new sentinels, and the high values of interest remain anchored to the full platform profiles.

## Current working hypotheses (explicit)

These hypotheses are **partial** and should be treated as such:

- `filter_arg_raw` is the historical `filter_arg` payload: a 16‑bit value whose meaning depends on the node’s tag and associated filter.
- For low values, `filter_arg_raw` maps directly into the current filter vocabulary (path/socket/iokit/etc.) and the literals/regex tables. This is well‑supported by both system profiles and probes.
- The high values we care about (16660, 2560, 10752, 165, 166, 170, 174, 115, 109, 3584, 0xffff) are **not** mis‑decoded filter IDs; instead they likely represent:
  - arguments to internal or profile‑local filters that do not appear in `filters.json`, or
  - payload values that drive special‑case logic in helpers (e.g., flow‑divert, default tails, system‑fcntls), possibly via equality comparisons or table lookups.
- There is no evidence on this host that the kernel splits `filter_arg_raw` into hi/lo bitfields via a standard mask (0x3fff/0x4000/0xc000) at the reader; any hi‑bit behavior (like 16660’s `0x4000` component) would have to be interpreted by higher‑level code, not by a generic “decode” step.

We explicitly do **not** know:

- Whether bsd’s 16660, airlock’s 10752/0xffff, or flow‑divert’s 2560 have a clean 1:1 mapping to a semantic concept (e.g., “bsd default tail”, “flow‑divert branch”, “system‑fcntls only”) or are just indices into auxiliary tables we haven’t reconstructed.
- Whether the same numeric values would play the same role on other macOS versions; all observations here are Sonoma‑specific.

## Potentially fruitful next steps

Given the current state of artifacts and tooling, the paths below look like they could still pay off without re‑treading old ground. They are phrased as small tasks that can be picked up independently.

### 1. Follow `filter_arg_raw` into concrete helpers

Now that `__read16` and `_eval` are located, the next kernel‑side step is to **track where the u16 payload actually drives behavior**:

- Use Ghidra on `com.apple.security.sandbox` to:
  - Identify all callers of `__read16` that forward its result to comparison or table‑index operations (e.g., `_match_network`, `_populate_syscall_mask`, or other helper families).
  - For each caller, annotate:
    - whether `filter_arg_raw` is compared directly against a small immediate (equality/inequality), or
    - used as part of an index into a table whose contents we can dump.
- If any caller shows comparisons against constants that match our unknowns (16660, 2560, 10752, 0xffff, 3584), record that as a candidate mapping in the experiment (not here), together with the surrounding control‑flow pattern.
- If callers only ever treat `filter_arg_raw` as an index into per‑profile tables without obvious constants, we should update this note to reflect that and shift focus toward reconstructing those tables instead.

### 2. Use op reach and tag layouts to bound semantics

Even without full helper semantics, the combination of op reach and tag layouts gives us structural constraints:

- For bsd 16660:
  - It sits on tag 0, with high fan‑in and reachability from ops 0–27. Check `book/graph/mappings/tag_layouts/tag_layouts.json` to confirm the meaning of tag 0’s successors.
  - Use `unknown_nodes.json` to:
    - verify all predecessors and the unique successor for 16660,
    - and confirm whether this tail is always the last decision stage for those operations.
  - This should let us describe 16660 as “a shared bsd tail with specific op coverage and tag shape,” even if we can’t name the filter.

- For airlock 165/166/10752/0xffff:
  - They are tightly tied to op 162 (`system-fcntl`) on tags 166/1/0.
  - Walk the small `airlock` graph (and the synthetic `airlock_system_fcntl` graph) with tag layouts in hand to see:
    - whether these nodes are early branch points or tails,
    - and how many distinct concrete predicates they appear to guard.
  - The aim is to refine the description from “high values in airlock” to “a small system‑fcntls‑only cluster with tag shapes X/Y/Z.”

- For flow‑divert 2560:
  - Use op reach and tag layouts to confirm it is genuinely op‑empty and structurally trivial (both successors to node 0) in the current decodes.
  - That gives us a precise structural bound: “unknown branch in mixed network probes, anchored on a flow‑divert literal, currently not reachable from any operation entrypoint in the decoded graphs.”

These steps won’t “solve” the unknowns, but they will tighten the structural story and make later helper‑level findings easier to slot into place.

### 3. Stop-gap probes guided by op reach (careful)

SBPL‑only probes have mostly hit diminishing returns, but one more **tightly guided** round might still be informative if we constrain it by op reach instead of by intuition:

- Starting from `unknown_nodes.json`, pick one or two unknowns and design probes that:
  - preserve the same op IDs and a minimal set of literals, and
  - adjust only the default decision or a single additional filter.
- The goal is not to make 16660/2560/etc. disappear (we’ve already done that by simplifying too aggressively), but to find *nearby* profiles where:
  - the same unknown persists but additional nodes around it are simple and interpretable, or
  - the unknown disappears in favor of a known filter ID, giving us a “before/after” pair we can reason about.

If another round of such probes also collapses to low IDs or spawns yet more sentinels, we should explicitly record that in `Report.md` and officially stop the SBPL branch until kernel work progresses.

### 4. Guardrails for any future mapping

Any eventual “mapping” from high `filter_arg_raw` values to semantic labels should:

- Be anchored in **both** static structure (node/tag/op placement, literal attachments) **and** kernel helper behavior (comparisons or table lookups).
- Remain version‑specific to this host (Sonoma 14.4.1, Apple Silicon).
- Be emitted first as experiment‑local annotations (e.g., in `field2_inventory.json` or a separate mapping file under `book/experiments/field2-filters/`), and only promoted into shared vocab/mappings after validation and cross‑consumer checks.

Until then, this trouble report should be read as: “we have a reasonably complete static atlas of where the weird `filter_arg_raw` values live, we know the kernel reads them as raw u16s, and we have a clear set of kernel‑side and structural steps that could turn specific constants into grounded concepts, but we are not there yet.”
