"""Logging and observer helpers for EntitlementJail probes."""

from __future__ import annotations

import datetime as dt
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from book.api import path_utils


REPO_ROOT = path_utils.find_repo_root(Path(__file__))
LOG_OBSERVER = (
    REPO_ROOT
    / "book"
    / "tools"
    / "entitlement"
    / "EntitlementJail.app"
    / "Contents"
    / "MacOS"
    / "sandbox-log-observer"
)

LOG_CAPTURE_REQUESTED_MODE = os.environ.get("EJ_LOG_MODE", "stream").lower()
LOG_CAPTURE_MODE = "stream" if LOG_CAPTURE_REQUESTED_MODE == "sandbox" else LOG_CAPTURE_REQUESTED_MODE
LOG_OBSERVER_MODE = os.environ.get("EJ_LOG_OBSERVER", "always").lower()
LOG_OBSERVER_LAST = os.environ.get("EJ_LOG_LAST", "10s")

try:
    LOG_OBSERVER_PAD_S = float(os.environ.get("EJ_LOG_PAD_S", "2.0"))
except Exception:
    LOG_OBSERVER_PAD_S = 2.0


def _safe_tag(tag: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in tag)


def log_capture_args(log_path: Path) -> Tuple[str, List[str], Optional[str]]:
    mode = LOG_CAPTURE_MODE
    if mode == "path_class":
        log_name = _safe_tag(log_path.name)
        return "path_class", ["--log-path-class", "tmp", "--log-name", log_name], log_name
    return "stream", ["--log-stream", str(log_path)], None


def extract_details(stdout_json: Optional[Dict[str, object]]) -> Optional[Dict[str, object]]:
    if not isinstance(stdout_json, dict):
        return None
    data = stdout_json.get("data")
    if isinstance(data, dict):
        details = data.get("details")
        if isinstance(details, dict):
            return details
    details = stdout_json.get("details")
    if isinstance(details, dict):
        return details
    return None


def extract_log_capture_path(stdout_json: Optional[Dict[str, object]]) -> Optional[str]:
    if not isinstance(stdout_json, dict):
        return None
    data = stdout_json.get("data")
    if isinstance(data, dict):
        log_path = data.get("log_capture_path")
        if isinstance(log_path, str):
            return log_path
    return None


def extract_log_capture_status(stdout_json: Optional[Dict[str, object]]) -> Optional[str]:
    if not isinstance(stdout_json, dict):
        return None
    data = stdout_json.get("data")
    if isinstance(data, dict):
        status = data.get("log_capture_status")
        if isinstance(status, str):
            return status
    return None


def extract_process_name(stdout_json: Optional[Dict[str, object]]) -> Optional[str]:
    details = extract_details(stdout_json)
    if details is None:
        return None
    process_name = details.get("process_name")
    return process_name if isinstance(process_name, str) else None


def extract_service_pid(stdout_json: Optional[Dict[str, object]]) -> Optional[str]:
    details = extract_details(stdout_json)
    if details is None:
        return None
    for key in ("service_pid", "probe_pid", "pid"):
        value = details.get(key)
        if isinstance(value, int):
            return str(value)
        if isinstance(value, str) and value:
            return value
    return None


def extract_correlation_id(stdout_json: Optional[Dict[str, object]]) -> Optional[str]:
    details = extract_details(stdout_json)
    if details is None:
        return None
    correlation_id = details.get("correlation_id")
    return correlation_id if isinstance(correlation_id, str) else None


def should_run_observer(stdout_json: Optional[Dict[str, object]]) -> bool:
    if LOG_OBSERVER_MODE == "disabled":
        return False
    if LOG_OBSERVER_MODE == "always":
        return True
    status = extract_log_capture_status(stdout_json)
    if status is None:
        return True
    return status != "captured"


def observer_status(observer: Optional[Dict[str, object]]) -> str:
    if observer is None:
        return "not_requested"
    skipped = observer.get("skipped")
    if skipped:
        return f"skipped:{skipped}"
    if observer.get("exit_code") == 0:
        return "ok"
    return "error"


def _format_time(ts: float) -> str:
    return dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def _observer_time_args(
    start_s: Optional[float],
    end_s: Optional[float],
    last: str,
) -> Tuple[List[str], Dict[str, object]]:
    if start_s is None or end_s is None:
        return ["--last", last], {
            "observer_window_mode": "last",
            "observer_window_last": last,
        }
    start = start_s - LOG_OBSERVER_PAD_S
    end = end_s + LOG_OBSERVER_PAD_S
    start_str = _format_time(start)
    end_str = _format_time(end)
    return ["--start", start_str, "--end", end_str], {
        "observer_window_mode": "range",
        "observer_window_start": start_str,
        "observer_window_end": end_str,
        "observer_window_pad_s": LOG_OBSERVER_PAD_S,
    }


def run_sandbox_log_observer(
    *,
    pid: Optional[str],
    process_name: Optional[str],
    dest_path: Path,
    last: str,
    start_s: Optional[float] = None,
    end_s: Optional[float] = None,
    plan_id: Optional[str] = None,
    row_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> Dict[str, object]:
    if pid is None or process_name is None:
        return {"skipped": "missing_pid_or_process_name"}
    if not LOG_OBSERVER.exists():
        return {
            "skipped": "observer_missing",
            "observer_path": path_utils.to_repo_relative(LOG_OBSERVER, REPO_ROOT),
        }

    time_args, window_meta = _observer_time_args(start_s, end_s, last)
    cmd = [str(LOG_OBSERVER), "--pid", str(pid), "--process-name", process_name, *time_args]
    if plan_id:
        cmd += ["--plan-id", plan_id]
    if row_id:
        cmd += ["--row-id", row_id]
    if correlation_id:
        cmd += ["--correlation-id", correlation_id]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
    except Exception as exc:
        return {
            "command": path_utils.relativize_command(cmd, REPO_ROOT),
            "error": f"{type(exc).__name__}: {exc}",
        }

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    write_error = None
    try:
        dest_path.write_text(res.stdout)
    except Exception as exc:
        write_error = f"{type(exc).__name__}: {exc}"

    return {
        "command": path_utils.relativize_command(cmd, REPO_ROOT),
        "exit_code": res.returncode,
        "stderr": res.stderr,
        "log_path": path_utils.to_repo_relative(dest_path, REPO_ROOT),
        "log_write_error": write_error,
        "pid": str(pid),
        "process_name": process_name,
        "last": last,
        "plan_id": plan_id,
        "row_id": row_id,
        "correlation_id": correlation_id,
        "stdout_bytes": len(res.stdout),
        **window_meta,
    }
