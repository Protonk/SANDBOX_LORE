# Agent “vibes” tests

This directory holds prompts and scenarios for **agentic tests** of the repo, rather than traditional unit tests.

- Files like `agent_layering.md` are self-contained instructions that can be handed to a fresh agent to exercise how well the layered `AGENTS.md` guidance and repo structure work in practice.
- These prompts are not executed by pytest; they are inputs for higher-level/manual evaluation of agent behavior and “vibes” against the project’s guardrails.

When adding new prompts:

- Keep each prompt self-contained and runnable without extra context.
- Focus on behaviors that test alignment with the substrate, concept inventory, mappings, and AGENTS layering (e.g., navigation, evidence discipline, or mapping hygiene).
