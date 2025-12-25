#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_ROOT="${ROOT_DIR}/out"
MATRIX_DIR="${OUT_ROOT}/matrix"
SUMMARY="${OUT_ROOT}/summary.md"

mkdir -p "${MATRIX_DIR}"

sw_vers_line="$(sw_vers | tr '\n' ';' | sed 's/;*$//')"
uname_line="$(uname -a)"

cat > "${SUMMARY}" <<EOF
# shrink-trace run matrix

Host (sw_vers): ${sw_vers_line}
Host (uname): ${uname_line}

| run | fixture | import_dyld_support | network_rules | success_streak | trace_status | iterations | trace_lines | shrunk_lines | bad_rules | shrink_removed | shrink_kept | fresh_rc | repeat_rc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
EOF

fixtures=("sandbox_target" "sandbox_net_required" "sandbox_spawn")
import_vals=(1 0)
network_rules=("parsed" "drop")
streaks=(2 3)

for fixture in "${fixtures[@]}"; do
  for import_dyld in "${import_vals[@]}"; do
    for net_rule in "${network_rules[@]}"; do
      for streak in "${streaks[@]}"; do
        label="${fixture}_dyld${import_dyld}_net${net_rule}_streak${streak}"
        run_dir="${MATRIX_DIR}/${label}"
        mkdir -p "${run_dir}"
        set +e
        OUT_DIR="${run_dir}" \
          FIXTURE_BIN="${fixture}" \
          IMPORT_DYLD_SUPPORT="${import_dyld}" \
          NETWORK_RULES="${net_rule}" \
          SUCCESS_STREAK="${streak}" \
          "${ROOT_DIR}/scripts/run_workflow.sh" > "${run_dir}/run.log" 2>&1
        set -e

        metrics="${run_dir}/metrics.tsv"
        trace_status="unknown"
        if [[ -f "${run_dir}/trace_status.txt" ]]; then
          trace_status="$(awk -F= '/^status=/{print $2}' "${run_dir}/trace_status.txt" | tail -n 1)"
        fi
        iterations="na"
        if [[ -f "${metrics}" ]]; then
          iterations="$(tail -n +2 "${metrics}" | wc -l | tr -d ' ')"
        fi
        trace_lines="na"
        if [[ -f "${run_dir}/profile.sb" ]]; then
          trace_lines="$(wc -l < "${run_dir}/profile.sb" | tr -d ' ')"
        fi
        shrunk_lines="na"
        if [[ -f "${run_dir}/profile.sb.shrunk" ]]; then
          shrunk_lines="$(wc -l < "${run_dir}/profile.sb.shrunk" | tr -d ' ')"
        fi
        bad_rules="na"
        if [[ -f "${run_dir}/bad_rules.txt" ]]; then
          bad_rules="$(wc -l < "${run_dir}/bad_rules.txt" | tr -d ' ')"
        fi
        shrink_removed="na"
        shrink_kept="na"
        if [[ -f "${run_dir}/shrink_stdout.txt" ]]; then
          shrink_removed="$(grep -c 'Removed line' "${run_dir}/shrink_stdout.txt" || true)"
          shrink_kept="$(grep -c 'Kept line' "${run_dir}/shrink_stdout.txt" || true)"
        fi
        fresh_rc="na"
        repeat_rc="na"
        if [[ -f "${run_dir}/post_shrink_fresh_exitcode.txt" ]]; then
          fresh_rc="$(cat "${run_dir}/post_shrink_fresh_exitcode.txt")"
        fi
        if [[ -f "${run_dir}/post_shrink_repeat_exitcode.txt" ]]; then
          repeat_rc="$(cat "${run_dir}/post_shrink_repeat_exitcode.txt")"
        fi

        echo "| ${label} | ${fixture} | ${import_dyld} | ${net_rule} | ${streak} | ${trace_status} | ${iterations} | ${trace_lines} | ${shrunk_lines} | ${bad_rules} | ${shrink_removed} | ${shrink_kept} | ${fresh_rc} | ${repeat_rc} |" >> "${SUMMARY}"
      done
    done
  done
done

echo "[+] Wrote summary: ${SUMMARY}"
