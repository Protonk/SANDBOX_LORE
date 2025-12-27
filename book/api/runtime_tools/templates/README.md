# runtime_tools templates

These are copy-and-edit templates for adding a new runtime probe family.
They are not referenced by the registry index and are safe to edit locally.

Suggested workflow:
1) Copy `plan.json` into your experiment as `book/experiments/<exp>/plan.json`.
2) Copy `probes.json` + `profiles.json` into `book/experiments/<exp>/registry/`.
3) Update the registry index (`book/api/runtime_tools/registry/index.json`) to point at the new registry.
4) Run `python -m book.api.runtime_tools registry-lint --registry <id>` and `plan-lint` before running.
