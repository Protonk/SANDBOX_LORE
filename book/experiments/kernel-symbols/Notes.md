# Notes

- Ghidra outputs for kernel symbols/strings are relocated to `book/experiments/kernel-symbols/out/<build>/kernel-symbols/`.
- Use the connector helper `run_task.py kernel-symbols --exec` to regenerate; defaults include ARM64 processor and the disable-x86 pre-script.
- Keep using `--process-existing --no-analysis` for downstream scripts to avoid rerunning analyzers.
