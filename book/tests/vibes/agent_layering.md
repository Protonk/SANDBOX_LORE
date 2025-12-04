You are an agent dropped into a code repository that uses layered `AGENTS.md` files to guide behavior.

Your task is to audit the **agent guidance layering** across the repo and report whether any changes are actually needed.

Do not assume any prior context beyond this prompt.

---

## Step 1 – Discover all AGENTS.md layerings

1. Start from the repository root (`.`).
2. Find every `AGENTS.md` file in the tree.
3. For each `AGENTS.md`, determine the **layering stack** that applies at its location:
   - The stack is the ordered list of `AGENTS.md` files from the root down to that directory.
   - Example of a stack shape (for illustration):  
     `AGENTS.md` → `book/AGENTS.md` → `book/graph/AGENTS.md` → `book/graph/concepts/AGENTS.md`.
4. Deduplicate by stack shape so you end up with a set of **unique AGENTS layerings** (each is a specific sequence of `AGENTS.md` files).

Your first intermediate result (for yourself) is a list like:

- `AGENTS.md`
- `AGENTS.md` → `book/AGENTS.md`
- `AGENTS.md` → `book/AGENTS.md` → `book/api/AGENTS.md`
- …

---

## Step 2 – Read each layering as *layered* instructions

For each unique layering stack:

1. Read the `AGENTS.md` files in **order from root to leaf**.
2. Treat them as **additive instructions**:
   - Higher-level files (`AGENTS.md` near the root) set global constraints and vocabulary.
   - Lower-level files (deeper subdirectories) are allowed to specialize or narrow, but **must not contradict** higher levels.

While reading, focus on three things:

1. **Inconsistencies**
   - Do any lower layers contradict higher layers on:
     - Host baseline (OS version, architecture, SIP status)?
     - Evidence model (what counts as primary evidence, how status is treated)?
     - Vocabulary discipline (which files define ops/filters/concepts)?
     - Allowed/forbidden actions (e.g., “don’t edit X” vs “edit X” below)?
   - If you find a real contradiction, that is a **problem**, not just a stylistic issue.

2. **Conceptual or cognitive friction**
   - Do lower layers re-state or reframe concepts in a way that:
     - Confuses or blurs earlier definitions (e.g., redefining “concept inventory” or “mapping” differently)?
     - Encourages a different mental model than what higher layers set up?
   - Repetition is fine; the issue is **confusing or conflicting restatement**, not simple overlap.

3. **Usefulness and specificity of the last layer**
   - Is the leaf `AGENTS.md` specific and actionable for that directory?
   - Does it:
     - Tell you clearly what files are sources vs generated?
     - Explain what *kind* of work is allowed/expected there?
     - Avoid repeating only generic repo-wide rules with no local detail?

---

## Step 3 – Decide if action is needed (low gate)

For each unique layering, decide whether actual changes are needed.

Important: the bar for changes is **low**—do not suggest edits just because something could be phrased better. Recommend changes only when there is a **real problem**, such as:

- A direct contradiction between layers.
- Strong cognitive friction where a lower layer clearly misleads relative to higher guidance.
- A leaf layer that is so vague that it fails to give any useful, local guidance for that directory.

If there is no real problem—only minor opportunities for polish or additional explanation—treat that as **“no action needed”**.

---

## Step 4 – Report format

Your first response to this task should be a concise report over **all** unique layerings you found, in the following format:

For each unique layering stack, list it and then say whether action is needed. If not, just say so. If yes, briefly describe what needs to change.

Example format (adapt to the actual layerings you find):

1. **`AGENTS.md`**  
   - Action: No action needed.

2. **`AGENTS.md` → `book/AGENTS.md` → `book/api/AGENTS.md`**  
   - Action: No action needed.

3. **`AGENTS.md` → `book/AGENTS.md` → `book/graph/AGENTS.md` → `book/graph/concepts/AGENTS.md`**  
   - Action: No action needed.  

4. **`AGENTS.md` → `book/AGENTS.md` → `book/experiments/AGENTS.md`**  
   - Action: Yes.  
   - Recommended change: [1–2 sentences describing the concrete inconsistency or serious friction and a specific fix, e.g., “Clarify that experiment outputs should not be written directly to book/graph/mappings; point to the generator script instead.”]

Constraints:

- Do **not** propose cosmetic or purely stylistic changes; only recommend action where the layering genuinely misguides or conflicts.
- Keep the report compact: one bullet group per layering, with at most 1–2 short sentences when action is needed.
- Do not output anything else (no extra analysis, no command logs).

