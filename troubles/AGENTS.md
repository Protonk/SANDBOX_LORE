# Agents in `troubles/`

This folder is a small scratchpad for things that broke or don’t add up. Check here when you’re hunting for:

- Repro steps for decoder/ingestion failures.
- Harness/apply/runtime errors that blocked an experiment.
- Mismatches between substrate theory and artifacts that haven’t been resolved.
- Notes on crashes or unexpected outputs from tools or profiles.

Entries should stay minimal but actionable: what was run, what failed, what was expected, and pointers to related experiments or mappings.

## How to add a trouble note

- Include: commands/inputs, observed failure, expected outcome (if relevant), and links/paths to affected artifacts.
- Keep it short and factual; no timestamps/dates.
- If resolved, add a one-liner (“resolved via …”) and point to the fix.

## Things to avoid

- Don’t stash large binaries or long logs; reference paths and include minimal snippets.
- Don’t treat this as another `out/` tree—troubles should point back to real artifacts under `book/` or `dumps/`.
- Don’t silently delete or overwrite prior notes; if superseded, note where the fix landed.
