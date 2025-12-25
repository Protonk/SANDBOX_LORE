#!/usr/bin/env bash
set -euo pipefail

# Instrumented shrinker: only removes a rule if both fresh and repeat runs succeed.

COMMAND="${1:-}"
SANDBOX_PROFILE="${2:-}"

if [[ -z "${COMMAND}" || -z "${SANDBOX_PROFILE}" ]]; then
  echo "Usage: shrink_instrumented.sh <executable name> <sandbox profile>"
  exit 2
fi

TEMP_SANDBOX_PROFILE="$(mktemp)"
WORK_DIR="${WORK_DIR:-$(pwd)}"
DYLD_LOG_PATH="${DYLD_LOG_PATH:-${WORK_DIR}/dyld.log}"
PARAM_ARGS=(-D "WORK_DIR=${WORK_DIR}" -D "DYLD_LOG_PATH=${DYLD_LOG_PATH}")

reset_workspace() {
  rm -rf ./out
}

run_under() {
  local profile="$1"
  set +e
  sandbox-exec "${PARAM_ARGS[@]}" -f "${profile}" ${COMMAND}
  local rc=$?
  set -e
  return "${rc}"
}

two_phase_check() {
  local profile="$1"
  reset_workspace
  echo "[-] Executing (fresh) ..."
  if ! run_under "${profile}"; then
    return 1
  fi
  echo "[-] Executing (repeat) ..."
  if ! run_under "${profile}"; then
    return 1
  fi
  return 0
}

if ! two_phase_check "${SANDBOX_PROFILE}"; then
  echo "[+] The command could not execute successfully with the initial sandbox profile provided."
  exit 1
else
  echo "[*] Successful execution of the command with initial sandbox (fresh + repeat)."
fi

LINE_COUNT=$(wc -l < "${SANDBOX_PROFILE}")
cp "${SANDBOX_PROFILE}" "${TEMP_SANDBOX_PROFILE}"

for (( i=LINE_COUNT; i>0; i-- ))
do
  TMP="$(mktemp)"
  sed "${i}d" "${TEMP_SANDBOX_PROFILE}" > "${TMP}"
  LINE="$(sed "${i}q;d" "${SANDBOX_PROFILE}")"

  echo "[-] Attempting to remove line $i: $LINE"
  if two_phase_check "${TMP}"; then
    if echo "${LINE}" | grep -q "([ ]*deny "; then
      echo "[*] Not removing a deny rule"
    else
      echo "[+] Removed line $i: unnecessary rule."
      cp "${TMP}" "${TEMP_SANDBOX_PROFILE}"
    fi
  else
    echo "[*] Kept line $i: necessary rule."
  fi
  rm -f "${TMP}"
done

echo "[-] Minimised sandbox profile:"
cat "${TEMP_SANDBOX_PROFILE}"
mv "${TEMP_SANDBOX_PROFILE}" "${SANDBOX_PROFILE}.shrunk"
