#!/bin/zsh
# Scaffold for Section 2.3 ("Tracing real operations through the sandbox").
# Safe to run: defaults to a dry-run that only prints intended tracing steps.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
BASE_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
TRACES_DIR="${BASE_DIR}/traces"

mkdir -p "${TRACES_DIR}"

usage() {
  cat <<'USAGE'
Usage: 02.3_trace_operations.sh [--run]

- Default mode: dry-run; prints the intended tracing commands and scenarios.
- --run: execute the tracing commands (may require elevated privileges and a GUI).

Planned mapping (user action -> expected trace hints):
- Open a file in ~/Documents: watch for file opens in user space and mach-lookup to tccd.
- Auto-save a document: look for writes under the container Data/Documents plus temp files.
- Print a document: expect I/O with printing services and potential sandbox extensions.

Traces would be stored under profiles/textedit/traces/.
USAGE
}

if [[ "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

run_mode="dry-run"
if [[ "${1:-}" == "--run" ]]; then
  run_mode="run"
fi

echo "Mode: ${run_mode}"
echo "Traces directory: ${TRACES_DIR}"

# Planned commands (commented out until tracing is desired):
# fs_usage example:
#   sudo fs_usage -w -f filesys -t 5 | tee "${TRACES_DIR}/fs_usage_open.txt"
# opensnoop example:
#   sudo opensnoop -p <TextEditPID> | tee "${TRACES_DIR}/opensnoop_open.txt"
# Future sandbox-specific tracer TODO:
#   sudo /path/to/sandbox_tracer --pid <TextEditPID> --output "${TRACES_DIR}/sandbox_trace.json"
#
# Start TextEdit (or placeholder process) for correlation:
#   open -a /System/Applications/TextEdit.app

if [[ "${run_mode}" == "dry-run" ]]; then
  echo "Dry-run only. Uncomment commands above or pass --run to attempt tracing."
  exit 0
fi

echo "Running simple placeholder checks..."
if command -v fs_usage >/dev/null 2>&1; then
  echo "fs_usage found; would run short capture into ${TRACES_DIR} (not implemented here)."
else
  echo "fs_usage not found in PATH."
fi

if command -v opensnoop >/dev/null 2>&1; then
  echo "opensnoop found; would attach to TextEdit PID (not implemented here)."
else
  echo "opensnoop not found in PATH."
fi

echo "TODO: implement actual tracing commands and mapping to SBPL rules."
