# Notes

- Use this file for run logs, harness quirks, and any unexpected runtime behavior. Avoid timestamps; prefer short factual entries tied to files or commands.
- Re-running `run_adversarial.py` inside the current harness caused `sandbox_init` to return EPERM for all probes (nested sandbox?), so artifacts remain from the prior successful host run with only the world_id metadata brought into line.
