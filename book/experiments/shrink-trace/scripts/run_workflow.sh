#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${OUT_DIR:-${ROOT_DIR}/out}"
REPO_ROOT="$(cd "${ROOT_DIR}/../../.." && pwd)"
LINT_SCRIPT="${ROOT_DIR}/scripts/lint_profile.py"
SEED_DYLD="${SEED_DYLD:-1}"
DENY_SIGSTOP="${DENY_SIGSTOP:-0}"
IMPORT_DYLD_SUPPORT="${IMPORT_DYLD_SUPPORT:-1}"
DYLD_LOG="${DYLD_LOG:-0}"
ALLOW_FIXTURE_EXEC="${ALLOW_FIXTURE_EXEC:-1}"
NETWORK_RULES="${NETWORK_RULES:-parsed}"
SUCCESS_STREAK="${SUCCESS_STREAK:-2}"
DENY_SCOPE="${DENY_SCOPE:-all}"
FIXTURE_BIN="${FIXTURE_BIN:-sandbox_target}"
WORLD_BASELINE="${REPO_ROOT}/book/world/sonoma-14.4.1-23E224-arm64/world-baseline.json"

WORLD_ID=""
if [[ -f "${WORLD_BASELINE}" ]]; then
  WORLD_ID="$(python3 - <<PY
import json
from pathlib import Path
path = Path("${WORLD_BASELINE}")
data = json.loads(path.read_text()) if path.exists() else {}
print(data.get("world_id", ""))
PY
)"
fi

DYLD_SUPPORT_PRESENT=0
if [[ -f "/System/Library/Sandbox/Profiles/dyld-support.sb" ]]; then
  DYLD_SUPPORT_PRESENT=1
fi

if [[ -d "${OUT_DIR}" ]]; then
  rm -rf "${OUT_DIR:?}"
fi
mkdir -p "${OUT_DIR}"
OUT_DIR="$(cd "${OUT_DIR}" && pwd)"
WORK_DIR="${OUT_DIR}"
DYLD_LOG_PATH="${DYLD_LOG_PATH:-${OUT_DIR}/dyld.log}"
PARAM_ARGS=(-D "WORK_DIR=${WORK_DIR}" -D "DYLD_LOG_PATH=${DYLD_LOG_PATH}")

if [[ "${OUT_DIR}" == "${REPO_ROOT}/"* ]]; then
  PROFILE_REL="${OUT_DIR#${REPO_ROOT}/}/profile.sb"
else
  PROFILE_REL="${OUT_DIR}/profile.sb"
fi

echo "[*] Output dir: ${OUT_DIR}"

# Ensure the program name resolves without a path, so killall behavior (if you run upstream)
# would match a process name. Here it also keeps command lines tidy.
export PATH="${OUT_DIR}:${PATH}"
export SEED_DYLD
export DENY_SIGSTOP
export IMPORT_DYLD_SUPPORT
export DYLD_LOG
export ALLOW_FIXTURE_EXEC
export NETWORK_RULES
export SUCCESS_STREAK
export DENY_SCOPE
export WORK_DIR
export DYLD_LOG_PATH
export WORLD_BASELINE

PROFILE="${OUT_DIR}/profile.sb"
TRACE_STATUS="${OUT_DIR}/trace_status.txt"
SUMMARY_FILE="${OUT_DIR}/run_summary.txt"
FIXTURE_PATH="${OUT_DIR}/${FIXTURE_BIN}"

# Build fixture into the selected output directory.
OUT_DIR="${OUT_DIR}" "${ROOT_DIR}/scripts/build_fixture.sh"

if [[ ! -x "${FIXTURE_PATH}" ]]; then
  echo "[!] Fixture not found or not executable: ${FIXTURE_PATH}"
  exit 1
fi

write_summary() {
  set +e
  iterations="na"
  if [[ -f "${OUT_DIR}/metrics.tsv" ]]; then
    iterations="$(tail -n +2 "${OUT_DIR}/metrics.tsv" | wc -l | tr -d ' ')"
  fi
  trace_lines="na"
  if [[ -f "${PROFILE}" ]]; then
    trace_lines="$(wc -l < "${PROFILE}" | tr -d ' ')"
  fi
  shrunk_lines="na"
  if [[ -f "${PROFILE}.shrunk" ]]; then
    shrunk_lines="$(wc -l < "${PROFILE}.shrunk" | tr -d ' ')"
  fi
  trace_status="unknown"
  if [[ -f "${TRACE_STATUS}" ]]; then
    trace_status="$(awk -F= '/^status=/{print $2}' "${TRACE_STATUS}" | tail -n 1)"
  fi
  bad_rules_count="na"
  if [[ -f "${OUT_DIR}/bad_rules.txt" ]]; then
    bad_rules_count="$(wc -l < "${OUT_DIR}/bad_rules.txt" | tr -d ' ')"
  fi
  shrink_removed="na"
  shrink_kept="na"
  if [[ -f "${OUT_DIR}/shrink_stdout.txt" ]]; then
    shrink_removed="$(grep -c 'Removed line' "${OUT_DIR}/shrink_stdout.txt" || true)"
    shrink_kept="$(grep -c 'Kept line' "${OUT_DIR}/shrink_stdout.txt" || true)"
  fi
  fresh_rc="na"
  repeat_rc="na"
  if [[ -f "${OUT_DIR}/post_shrink_fresh_exitcode.txt" ]]; then
    fresh_rc="$(cat "${OUT_DIR}/post_shrink_fresh_exitcode.txt")"
  fi
  if [[ -f "${OUT_DIR}/post_shrink_repeat_exitcode.txt" ]]; then
    repeat_rc="$(cat "${OUT_DIR}/post_shrink_repeat_exitcode.txt")"
  fi
  sw_vers_line="$(sw_vers | tr '\n' ';' | sed 's/;*$//')"
  uname_line="$(uname -a)"
  cat > "${SUMMARY_FILE}" <<EOF
world_id=${WORLD_ID}
sw_vers=${sw_vers_line}
uname=${uname_line}
fixture=${FIXTURE_BIN}
out_dir=${OUT_DIR}
import_dyld_support=${IMPORT_DYLD_SUPPORT}
dyld_support_present=${DYLD_SUPPORT_PRESENT}
network_rules=${NETWORK_RULES}
success_streak=${SUCCESS_STREAK}
deny_scope=${DENY_SCOPE}
dyld_log=${DYLD_LOG}
allow_fixture_exec=${ALLOW_FIXTURE_EXEC}
trace_status=${trace_status}
iterations=${iterations}
trace_lines=${trace_lines}
shrunk_lines=${shrunk_lines}
bad_rules=${bad_rules_count}
shrink_removed=${shrink_removed}
shrink_kept=${shrink_kept}
post_shrink_fresh_rc=${fresh_rc}
post_shrink_repeat_rc=${repeat_rc}
EOF
  set -e
}

trap write_summary EXIT

echo "[*] Tracing to build profile: ${PROFILE}"
(
  cd "${OUT_DIR}"
  "${ROOT_DIR}/scripts/trace_instrumented.sh" "./${FIXTURE_BIN}" "${PROFILE}" | tee "${OUT_DIR}/trace_stdout.txt"
)

if [[ "${DENY_SIGSTOP}" -eq 1 ]]; then
  echo "[*] DENY_SIGSTOP=1; skipping sandbox_min check to avoid SIGSTOP stalls."
else
  echo "[*] Sandbox-min check"
  (
    cd "${OUT_DIR}"
    set +e
    if [[ "${DYLD_LOG}" -eq 1 ]]; then
      DYLD_PRINT_TO_FILE="${DYLD_LOG_PATH}" \
        DYLD_PRINT_LIBRARIES=1 \
        DYLD_PRINT_INITIALIZERS=1 \
        sandbox-exec "${PARAM_ARGS[@]}" -f "${PROFILE}" ./sandbox_min > "${OUT_DIR}/sandbox_min_stdout.txt" 2> "${OUT_DIR}/sandbox_min_stderr.txt"
    else
      sandbox-exec "${PARAM_ARGS[@]}" -f "${PROFILE}" ./sandbox_min > "${OUT_DIR}/sandbox_min_stdout.txt" 2> "${OUT_DIR}/sandbox_min_stderr.txt"
    fi
    echo $? > "${OUT_DIR}/sandbox_min_exitcode.txt"
  )
fi

trace_status="unknown"
stall_dir=""
if [[ -f "${TRACE_STATUS}" ]]; then
  trace_status="$(awk -F= '/^status=/{print $2}' "${TRACE_STATUS}" | tail -n 1)"
  stall_dir="$(awk -F= '/^stall_dir=/{print $2}' "${TRACE_STATUS}" | tail -n 1)"
fi

if [[ "${trace_status}" != "success" ]]; then
  echo "[!] Trace status: ${trace_status}; skipping shrink."
  if [[ -n "${stall_dir}" ]]; then
    echo "[!] Stall bundle: ${stall_dir}"
  fi
  exit 0
fi

if [[ "${DENY_SIGSTOP}" -eq 1 ]]; then
  echo "[*] DENY_SIGSTOP=1; skipping pre-shrink validation and shrink."
  exit 0
fi

echo "[*] Preflight scan (trace profile)"
if (cd "${REPO_ROOT}" && python3 book/tools/preflight/preflight.py scan "${PROFILE_REL}" > "${OUT_DIR}/preflight_scan.json"); then
  :
else
  preflight_rc=$?
  echo "[!] Preflight scan failed (rc=${preflight_rc}); see ${OUT_DIR}/preflight_scan.json"
  exit "${preflight_rc}"
fi

echo "[*] Preflight scan OK; validating repeatable execution"
set +e
(
  set +e
  cd "${OUT_DIR}"
  sandbox-exec "${PARAM_ARGS[@]}" -f "${PROFILE}" "./${FIXTURE_BIN}" > "${OUT_DIR}/pre_shrink_run1_stdout.txt" 2> "${OUT_DIR}/pre_shrink_run1_stderr.txt"
  echo $? > "${OUT_DIR}/pre_shrink_run1_exitcode.txt"
  sandbox-exec "${PARAM_ARGS[@]}" -f "${PROFILE}" "./${FIXTURE_BIN}" > "${OUT_DIR}/pre_shrink_run2_stdout.txt" 2> "${OUT_DIR}/pre_shrink_run2_stderr.txt"
  echo $? > "${OUT_DIR}/pre_shrink_run2_exitcode.txt"
)
set -e
pre_rc1="$(cat "${OUT_DIR}/pre_shrink_run1_exitcode.txt")"
pre_rc2="$(cat "${OUT_DIR}/pre_shrink_run2_exitcode.txt")"
if [[ "${pre_rc1}" -ne 0 || "${pre_rc2}" -ne 0 ]]; then
  echo "[!] Pre-shrink validation failed (rc1=${pre_rc1}, rc2=${pre_rc2}); skipping shrink."
  exit 0
fi

echo "[*] Linting traced profile"
set +e
python3 "${LINT_SCRIPT}" "${PROFILE}" > "${OUT_DIR}/lint_profile_trace.txt"
lint_rc=$?
set -e
if [[ "${lint_rc}" -ne 0 ]]; then
  echo "[!] Lint failed for traced profile; see ${OUT_DIR}/lint_profile_trace.txt"
  exit 0
fi

echo "[*] Repeatable execution OK; proceeding to shrink"
echo "[*] Shrinking profile"

(
  cd "${OUT_DIR}"
  "${ROOT_DIR}/scripts/shrink_instrumented.sh" "./${FIXTURE_BIN}" "${PROFILE}" | tee "${OUT_DIR}/shrink_stdout.txt"
)

echo "[*] Linting shrunk profile"
set +e
python3 "${LINT_SCRIPT}" "${PROFILE}.shrunk" > "${OUT_DIR}/lint_profile_shrunk.txt"
lint_shrunk_rc=$?
set -e
if [[ "${lint_shrunk_rc}" -ne 0 ]]; then
  echo "[!] Lint failed for shrunk profile; see ${OUT_DIR}/lint_profile_shrunk.txt"
  exit 0
fi

echo "[*] Validating shrunk profile (fresh + repeat)"
set +e
(
  cd "${OUT_DIR}"
  rm -rf ./out
  sandbox-exec "${PARAM_ARGS[@]}" -f "${PROFILE}.shrunk" "./${FIXTURE_BIN}" > "${OUT_DIR}/post_shrink_fresh_stdout.txt" 2> "${OUT_DIR}/post_shrink_fresh_stderr.txt"
  echo $? > "${OUT_DIR}/post_shrink_fresh_exitcode.txt"
  sandbox-exec "${PARAM_ARGS[@]}" -f "${PROFILE}.shrunk" "./${FIXTURE_BIN}" > "${OUT_DIR}/post_shrink_repeat_stdout.txt" 2> "${OUT_DIR}/post_shrink_repeat_stderr.txt"
  echo $? > "${OUT_DIR}/post_shrink_repeat_exitcode.txt"
)
set -e
post_fresh_rc="$(cat "${OUT_DIR}/post_shrink_fresh_exitcode.txt")"
post_repeat_rc="$(cat "${OUT_DIR}/post_shrink_repeat_exitcode.txt")"
if [[ "${post_fresh_rc}" -ne 0 || "${post_repeat_rc}" -ne 0 ]]; then
  echo "[!] Shrunk profile failed validation (fresh=${post_fresh_rc}, repeat=${post_repeat_rc}); keeping full profile as working artifact."
  exit 0
fi

echo "[+] Done. Outputs:"
echo "    ${OUT_DIR}/profile.sb"
echo "    ${OUT_DIR}/profile.sb.shrunk"
echo "    ${OUT_DIR}/metrics.tsv"
echo "    ${OUT_DIR}/logs/"
echo "    ${OUT_DIR}/trace_stdout.txt"
echo "    ${OUT_DIR}/shrink_stdout.txt"
