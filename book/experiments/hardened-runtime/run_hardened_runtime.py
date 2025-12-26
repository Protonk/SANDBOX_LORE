#!/usr/bin/env python3
"""
Hardened runtime harness for non-VFS sandbox surfaces.

Runs probe families via the shared runtime_tools harness, records clean-channel
preflight, and emits baseline + decision-stage outputs with bounded mismatches.
"""
from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import errno
import json
import os
import plistlib
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from book.api import path_utils
from book.api.runtime_tools import workflow
from book.api.runtime_tools.core import contract as rt_contract
from book.api.runtime_tools.core.normalize import write_matrix_observations

from probes import build_all_profiles
import mismatch_packets

OUT_DIR = BASE_DIR / "out"
SB_DIR = BASE_DIR / "sb"
WORLD_PATH = REPO_ROOT / "book" / "world" / "sonoma-14.4.1-23E224-arm64" / "world-baseline.json"
APPLY_PREFLIGHT_PROFILE = SB_DIR / "apply_preflight_allow.sb"
SANDBOX_RUNNER = REPO_ROOT / "book" / "experiments" / "runtime-checks" / "sandbox_runner"
MACH_PROBE = REPO_ROOT / "book" / "experiments" / "runtime-checks" / "mach_probe"
SYSCTL = Path("/usr/sbin/sysctl")
NC = Path("/usr/bin/nc")
NOTIFYUTIL = Path("/usr/bin/notifyutil")
PYTHON = Path("/usr/bin/python3")
CODESIGN = Path("/usr/bin/codesign")
LAUNCHCTL = Path("/bin/launchctl")
LOG_CMD = Path("/usr/bin/log")

BASELINE_RESULTS = OUT_DIR / "baseline_results.json"
APPLY_PREFLIGHT_OUT = OUT_DIR / "apply_preflight.json"
SUMMARY_JSON = OUT_DIR / "summary.json"
SUMMARY_MD = OUT_DIR / "summary.md"
ORACLE_RESULTS = OUT_DIR / "oracle_results.json"
ARTIFACT_INDEX = OUT_DIR / "artifact_index.json"

BASELINE_SCHEMA_VERSION = "hardened-runtime.baseline_results.v0.2"
ORACLE_SCHEMA_VERSION = "hardened-runtime.oracle_results.v0.2"
SUMMARY_SCHEMA_VERSION = "hardened-runtime.summary.v0.2"
RUNTIME_RESULTS_SCHEMA_VERSION = "hardened-runtime.runtime_results.v0.2"
ARTIFACT_INDEX_SCHEMA_VERSION = "hardened-runtime.artifact_index.v0.1"
PROBE_DETAILS_SCHEMA_VERSION = "hardened-runtime.signal-probe.v0.2"

FILTER_HINTS = {
    "mach-lookup": "global-name",
    "sysctl-read": "sysctl-name",
    "darwin-notification-post": "notification-name",
    "distributed-notification-post": "notification-name",
    "signal": "target",
    "process-info-pidinfo": "target",
}

_LIBPROC = None
_PROC_PIDPATH = None
_LIBPROC_ERROR = None


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def load_world_id() -> str:
    data = json.loads(WORLD_PATH.read_text())
    return data.get("world_id") or data.get("id")


def _extract_plist(text: str) -> Optional[bytes]:
    start = text.find("<?xml")
    if start == -1:
        return None
    end = text.rfind("</plist>")
    if end == -1:
        return None
    return text[start : end + len("</plist>")].encode("utf-8")


_ENTITLEMENTS_CACHE: Dict[str, Dict[str, Any]] = {}


def _entitlement_info(path: Path) -> Dict[str, Any]:
    key = str(path)
    cached = _ENTITLEMENTS_CACHE.get(key)
    if cached:
        return cached
    info: Dict[str, Any] = {
        "binary": path_utils.to_repo_relative(path, repo_root=REPO_ROOT),
        "source": "codesign",
    }
    if not path.exists():
        info["error"] = "missing_binary"
        _ENTITLEMENTS_CACHE[key] = info
        return info
    try:
        res = subprocess.run(
            [str(CODESIGN), "-d", "--entitlements", "-", str(path)],
            capture_output=True,
            text=True,
        )
        output = (res.stderr or "") + (res.stdout or "")
        plist_bytes = _extract_plist(output)
        entitlements: Dict[str, Any] = {}
        if plist_bytes:
            entitlements = plistlib.loads(plist_bytes)
        has_app_sandbox = entitlements.get("com.apple.security.app-sandbox")
        info["has_app_sandbox_entitlement"] = bool(has_app_sandbox) if has_app_sandbox is not None else False
        info["entitlements_present"] = bool(entitlements)
        if res.returncode != 0:
            info["error"] = f"codesign_rc_{res.returncode}"
    except Exception as exc:
        info["error"] = str(exc)
    _ENTITLEMENTS_CACHE[key] = info
    return info


def _sandbox_check_self() -> Dict[str, Any]:
    info: Dict[str, Any] = {"source": "sandbox_check"}
    try:
        lib = ctypes.CDLL("libsystem_sandbox.dylib", use_errno=True)
        fn = lib.sandbox_check
        fn.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
        fn.restype = ctypes.c_int
        rc = fn(os.getpid(), None, 0)
        err = ctypes.get_errno()
        info["rc"] = int(rc)
        if err:
            info["errno"] = int(err)
            info["errno_name"] = errno.errorcode.get(err)
    except Exception as exc:
        info["error"] = str(exc)
    return info


def _load_libproc() -> Optional[str]:
    global _LIBPROC, _PROC_PIDPATH, _LIBPROC_ERROR
    if _LIBPROC is not None or _LIBPROC_ERROR is not None:
        return _LIBPROC_ERROR
    lib = ctypes.util.find_library("proc")
    if not lib:
        _LIBPROC_ERROR = "libproc_not_found"
        return _LIBPROC_ERROR
    try:
        _LIBPROC = ctypes.CDLL(lib, use_errno=True)
        _PROC_PIDPATH = _LIBPROC.proc_pidpath
        _PROC_PIDPATH.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
        _PROC_PIDPATH.restype = ctypes.c_int
        _LIBPROC_ERROR = None
    except Exception as exc:
        _LIBPROC = None
        _PROC_PIDPATH = None
        _LIBPROC_ERROR = str(exc)
    return _LIBPROC_ERROR


def _libproc_pidpath(pid: int) -> Dict[str, Any]:
    err = _load_libproc()
    if err:
        return {"error": err}
    buf = ctypes.create_string_buffer(4096)
    rc = _PROC_PIDPATH(pid, buf, ctypes.sizeof(buf))
    if rc <= 0:
        errnum = ctypes.get_errno()
        return {"error": "proc_pidpath_failed", "errno": errnum}
    return {"path": buf.value.decode("utf-8", errors="replace")}


def _parent_chain() -> List[Dict[str, Any]]:
    pid = os.getpid()
    ppid = os.getppid()
    chain = []
    chain.append({"pid": pid, "ppid": ppid, "path": _libproc_pidpath(pid).get("path")})
    chain.append({"pid": ppid, "path": _libproc_pidpath(ppid).get("path")})
    return chain


def _run_launchctl_procinfo(pid: int) -> Dict[str, Any]:
    record: Dict[str, Any] = {"pid": pid, "command": [str(LAUNCHCTL), "procinfo", str(pid)]}
    if not LAUNCHCTL.exists():
        record["status"] = "missing"
        return record
    try:
        res = subprocess.run(record["command"], capture_output=True, text=True, timeout=5)
        record.update(
            {
                "status": "ok" if res.returncode == 0 else "error",
                "returncode": res.returncode,
                "raw": (res.stdout or "") + (res.stderr or ""),
            }
        )
    except subprocess.TimeoutExpired:
        record.update({"status": "error", "error": "timeout"})
    except Exception as exc:
        record.update({"status": "error", "error": str(exc)})
    return record


def _probe_log_access() -> Dict[str, Any]:
    record: Dict[str, Any] = {"command": [str(LOG_CMD), "show", "--last", "1m", "--predicate", 'process == "sandboxd"', "--style", "syslog"]}
    if not LOG_CMD.exists():
        record["status"] = "missing"
        return record
    try:
        res = subprocess.run(record["command"], capture_output=True, text=True, timeout=5)
        record.update(
            {
                "status": "ok" if res.returncode == 0 else "error",
                "returncode": res.returncode,
                "denied": "not permitted" in (res.stderr or "").lower(),
                "stderr": (res.stderr or "")[-200:],
            }
        )
    except subprocess.TimeoutExpired:
        record.update({"status": "error", "error": "timeout"})
    except Exception as exc:
        record.update({"status": "error", "error": str(exc)})
    return record


def _derive_outer_attribution(procinfo: List[Dict[str, Any]], parent_chain: List[Dict[str, Any]]) -> Dict[str, Any]:
    attribution = {"status": "unknown", "tier": "partial", "source": None}
    if parent_chain:
        launcher = parent_chain[-1]
        attribution.update(
            {
                "status": "partial",
                "source": "libproc_parent_chain",
                "launcher": {
                    "pid": launcher.get("pid"),
                    "path": launcher.get("path"),
                },
                "notes": "launchctl procinfo unavailable or not parsed",
            }
        )
    if procinfo:
        root_required = any("requires root" in (entry.get("raw") or "").lower() for entry in procinfo)
        if root_required:
            attribution["procinfo_requires_root"] = True
    return attribution


def _classify_apply_gate_reason(app_sandbox: bool, apply_report: Optional[Dict[str, Any]]) -> str:
    if app_sandbox:
        return "runner_has_app_sandbox_entitlement"
    if not apply_report:
        return "unknown"
    err_class = apply_report.get("err_class")
    if err_class == "already_sandboxed":
        return "already_sandboxed"
    if err_class == "errno_eperm":
        return "nested_sandbox_environment"
    if apply_report.get("rc") not in (0, None):
        return "sandbox_init_api_denied"
    return "unknown"


def run_apply_preflight(world_id: str) -> Dict[str, Any]:
    run_id = os.environ.get("SANDBOX_LORE_RUN_ID")
    parent_chain = _parent_chain()
    procinfo = [_run_launchctl_procinfo(row.get("pid")) for row in parent_chain if row.get("pid")]
    record: Dict[str, Any] = {
        "world_id": world_id,
        "run_id": run_id,
        "profile": path_utils.to_repo_relative(APPLY_PREFLIGHT_PROFILE, repo_root=REPO_ROOT),
        "runner": path_utils.to_repo_relative(SANDBOX_RUNNER, repo_root=REPO_ROOT),
        "parent_chain": parent_chain,
        "procinfo": procinfo,
        "runner_entitlements": _entitlement_info(SANDBOX_RUNNER),
        "sandbox_check_self": _sandbox_check_self(),
    }
    if not APPLY_PREFLIGHT_PROFILE.exists():
        record["status"] = "error"
        record["error"] = "missing_preflight_profile"
        return record
    if not SANDBOX_RUNNER.exists():
        record["status"] = "error"
        record["error"] = "missing_sandbox_runner"
        return record
    cmd = [str(SANDBOX_RUNNER), str(APPLY_PREFLIGHT_PROFILE), "--", "/usr/bin/true"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        stderr = res.stderr or ""
        apply_markers = rt_contract.extract_sbpl_apply_markers(stderr)
        apply_report = rt_contract.derive_apply_report_from_markers(apply_markers) if apply_markers else None
        err_class = apply_report.get("err_class") if isinstance(apply_report, dict) else None
        preexisting = err_class in {"already_sandboxed", "errno_eperm"}
        blocked_reason = _classify_apply_gate_reason(
            bool(record["runner_entitlements"].get("has_app_sandbox_entitlement")), apply_report
        )
        record.update(
            {
                "status": "ok",
                "command": path_utils.relativize_command(cmd, repo_root=REPO_ROOT),
                "exit_code": res.returncode,
                "stdout": res.stdout,
                "stderr": rt_contract.strip_tool_markers(stderr),
                "apply_report": apply_report,
                "apply_marker_pid": (apply_markers[0].get("pid") if apply_markers else None),
                "apply_ok": bool(apply_report and apply_report.get("rc") == 0),
                "failure_stage": "apply" if apply_report and apply_report.get("rc") not in (0, None) else None,
                "preexisting_sandbox_suspected": preexisting,
                "blocked_reason": blocked_reason,
                "outer_sandbox_attribution": _derive_outer_attribution(procinfo, parent_chain),
                "fingerprint": {
                    "launchctl_procinfo": {
                        "attempted": True,
                        "requires_root": any(
                            "requires root" in (entry.get("raw") or "").lower() for entry in procinfo if isinstance(entry, dict)
                        ),
                    },
                    "log_show": _probe_log_access(),
                    "proc_pidpath": {
                        "self": _libproc_pidpath(os.getpid()),
                        "parent": _libproc_pidpath(os.getppid()),
                    },
                },
            }
        )
    except Exception as exc:
        record["status"] = "error"
        record["error"] = str(exc)
    return record


def _probe_command(op: str, target: Optional[str]) -> List[str]:
    if op == "mach-lookup" and MACH_PROBE.exists() and target:
        return [str(MACH_PROBE), target]
    if op == "sysctl-read" and SYSCTL.exists() and target:
        return [str(SYSCTL), "-n", target]
    if op == "darwin-notification-post" and NOTIFYUTIL.exists() and target:
        return [str(NOTIFYUTIL), "-p", target]
    if op == "distributed-notification-post" and PYTHON.exists() and target:
        script = (
            "import ctypes, sys\n"
            "cf = ctypes.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')\n"
            "cf.CFNotificationCenterGetDistributedCenter.restype = ctypes.c_void_p\n"
            "center = cf.CFNotificationCenterGetDistributedCenter()\n"
            "cf.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]\n"
            "cf.CFStringCreateWithCString.restype = ctypes.c_void_p\n"
            "kCFStringEncodingUTF8 = 0x08000100\n"
            "name = sys.argv[1].encode('utf-8')\n"
            "cfname = cf.CFStringCreateWithCString(None, name, kCFStringEncodingUTF8)\n"
            "cf.CFNotificationCenterPostNotification.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_bool]\n"
            "cf.CFNotificationCenterPostNotification(center, cfname, None, None, True)\n"
        )
        return [str(PYTHON), "-c", script, target]
    if op == "process-info-pidinfo" and PYTHON.exists() and target:
        script = (
            "import ctypes, ctypes.util, os, sys\n"
            "lib = ctypes.CDLL(ctypes.util.find_library('proc'))\n"
            "lib.proc_pidinfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_int]\n"
            "lib.proc_pidinfo.restype = ctypes.c_int\n"
            "PROC_PIDTBSDINFO = 3\n"
            "pid_arg = sys.argv[1]\n"
            "pid = os.getpid() if pid_arg == 'self' else int(pid_arg)\n"
            "buf = ctypes.create_string_buffer(512)\n"
            "rc = lib.proc_pidinfo(pid, PROC_PIDTBSDINFO, 0, buf, ctypes.sizeof(buf))\n"
            "sys.exit(0 if rc > 0 else 1)\n"
        )
        return [str(PYTHON), "-c", script, target]
    if op == "signal" and PYTHON.exists():
        script = (
            "import json, os, signal, subprocess, sys\n"
            "ready_r, ready_w = os.pipe()\n"
            "result_r, result_w = os.pipe()\n"
            "child_env = os.environ.copy()\n"
            "child_env['SBL_READY_FD'] = str(ready_w)\n"
            "child_env['SBL_RESULT_FD'] = str(result_w)\n"
            "child_code = (\n"
            "    \"import os, signal, sys\\n\"\n"
            "    \"ready_fd = int(os.environ.get('SBL_READY_FD', '-1'))\\n\"\n"
            "    \"result_fd = int(os.environ.get('SBL_RESULT_FD', '-1'))\\n\"\n"
            "    \"def handler(signum, frame):\\n\"\n"
            "    \"    try: os.write(result_fd, b'signal')\\n\"\n"
            "    \"    except Exception: pass\\n\"\n"
            "    \"    sys.exit(0)\\n\"\n"
            "    \"signal.signal(signal.SIGUSR1, handler)\\n\"\n"
            "    \"try: os.write(ready_fd, b'ready')\\n\"\n"
            "    \"except Exception: pass\\n\"\n"
            "    \"signal.pause()\\n\"\n"
            "    \"sys.exit(2)\\n\"\n"
            ")\n"
            "child = subprocess.Popen([sys.executable, '-c', child_code], pass_fds=(ready_w, result_w), env=child_env)\n"
            "os.close(ready_w)\n"
            "os.close(result_w)\n"
            "details = {\n"
            "    'probe_schema_version': '" + PROBE_DETAILS_SCHEMA_VERSION + "',\n"
            "    'child_pid': child.pid,\n"
            "    'child_spawn_method': 'subprocess.Popen',\n"
            "    'handshake_ok': False,\n"
            "    'signal_sent': False,\n"
            "    'child_received_signal': False,\n"
            "}\n"
            "try:\n"
            "    data = os.read(ready_r, 5)\n"
            "    details['handshake_ok'] = data == b'ready'\n"
            "except Exception as exc:\n"
            "    details['handshake_error'] = str(exc)\n"
            "if details['handshake_ok']:\n"
            "    try:\n"
            "        os.kill(child.pid, signal.SIGUSR1)\n"
            "        details['signal_sent'] = True\n"
            "    except Exception as exc:\n"
            "        details['signal_error'] = str(exc)\n"
            "try:\n"
            "    import select\n"
            "    rlist, _, _ = select.select([result_r], [], [], 1.0)\n"
            "    if rlist:\n"
            "        data = os.read(result_r, 16)\n"
            "        if data.startswith(b'signal'):\n"
            "            details['child_received_signal'] = True\n"
            "except Exception as exc:\n"
            "    details['result_error'] = str(exc)\n"
            "try:\n"
            "    child.wait(timeout=1.0)\n"
            "    details['child_exit_code'] = child.returncode\n"
            "    details['child_status'] = 'exited'\n"
            "except Exception:\n"
            "    child.kill()\n"
            "    child.wait()\n"
            "    details['child_exit_code'] = child.returncode\n"
            "    details['child_status'] = 'killed'\n"
            "print('SBL_PROBE_DETAILS ' + json.dumps(details))\n"
            "sys.exit(0 if details['signal_sent'] and details['child_received_signal'] else 1)\n"
        )
        return [str(PYTHON), "-c", script]
    if op == "network-outbound" and NC.exists() and target:
        host = target
        port = "80"
        if ":" in target:
            host, port = target.split(":", 1)
        return [str(NC), "-z", "-w", "2", host, port]
    return ["true"]


def _extract_probe_details(stdout: str | None) -> tuple[Optional[Dict[str, Any]], str]:
    if not stdout:
        return None, ""
    details: Optional[Dict[str, Any]] = None
    cleaned_lines: List[str] = []
    for line in stdout.splitlines():
        if line.startswith("SBL_PROBE_DETAILS "):
            payload = line[len("SBL_PROBE_DETAILS ") :].strip()
            if payload:
                try:
                    details = json.loads(payload)
                except Exception:
                    details = {"error": "invalid_probe_details_json"}
            continue
        cleaned_lines.append(line)
    cleaned = "\n".join(cleaned_lines)
    if stdout.endswith("\n") and cleaned:
        cleaned += "\n"
    return details, cleaned


def _baseline_for_probe(profile_id: str, probe: Dict[str, Any]) -> Dict[str, Any]:
    op = probe.get("operation") or ""
    target = probe.get("target")
    cmd = _probe_command(op, target)
    record: Dict[str, Any] = {
        "name": f"baseline:{profile_id}:{probe.get('name')}",
        "profile_id": profile_id,
        "probe_name": probe.get("name"),
        "operation": op,
        "target": target,
        "primary_intent": {
            "operation": op,
            "target": target,
            "profile_id": profile_id,
            "probe_name": probe.get("name"),
        },
        "command": path_utils.relativize_command(cmd, repo_root=REPO_ROOT),
    }
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        probe_details, stdout_clean = _extract_probe_details(res.stdout or "")
        record["status"] = "allow" if res.returncode == 0 else "deny"
        record["exit_code"] = res.returncode
        record["stdout"] = stdout_clean[:200]
        record["stderr"] = (res.stderr or "")[:200]
        record["reached_primary_op"] = True
        record["decision_path"] = "baseline"
        if probe_details is not None:
            record["probe_details"] = probe_details
    except subprocess.TimeoutExpired:
        record["status"] = "deny"
        record["error"] = "timeout"
    except Exception as exc:
        record["status"] = "deny"
        record["error"] = str(exc)
    return record


def _decision_path(runtime_result: Dict[str, Any], actual: Optional[str]) -> str:
    stage = runtime_result.get("failure_stage")
    if stage in {"apply", "preflight", "bootstrap"}:
        return "dependency_denied"
    if actual == "deny":
        return "primary_op_denied"
    if actual == "allow":
        return "no_denial_observed"
    return "unknown"


def _first_denial_op(
    op: Optional[str],
    decision_path: str,
    runtime_result: Dict[str, Any],
) -> Optional[str]:
    if decision_path == "primary_op_denied":
        return op
    if decision_path == "dependency_denied":
        if runtime_result.get("failure_kind") == "bootstrap_deny_process_exec":
            return "process-exec*"
    return None


def _first_denial_filters(op: Optional[str], target: Optional[str], decision_path: str) -> Optional[List[Dict[str, Any]]]:
    if decision_path != "primary_op_denied":
        return None
    if not op or not target:
        return None
    hint = FILTER_HINTS.get(op)
    if not hint:
        return None
    return [{"name": hint, "value": target}]


def _annotate_runtime_results(path: Path) -> None:
    data = json.loads(path.read_text())
    for profile_id, profile in data.items():
        if not isinstance(profile, dict):
            continue
        profile["schema_version"] = RUNTIME_RESULTS_SCHEMA_VERSION
        if os.environ.get("SANDBOX_LORE_RUN_ID"):
            profile["run_id"] = os.environ.get("SANDBOX_LORE_RUN_ID")
        probes = profile.get("probes") or []
        for probe in probes:
            op = probe.get("operation")
            target = probe.get("path") or probe.get("target")
            runtime_result = probe.get("runtime_result") or {}
            actual = probe.get("actual")
            decision_path = _decision_path(runtime_result, actual)
            first_op = _first_denial_op(op, decision_path, runtime_result)
            probe["primary_intent"] = {
                "operation": op,
                "target": target,
                "profile_id": profile_id,
                "probe_name": probe.get("name"),
            }
            probe["reached_primary_op"] = decision_path != "dependency_denied"
            probe["decision_path"] = decision_path
            probe["first_denial_op"] = first_op
            probe["first_denial_filters"] = _first_denial_filters(op, target, decision_path)
            if probe.get("probe_details") is None:
                details, _ = _extract_probe_details(probe.get("stdout"))
                if details is not None:
                    probe["probe_details"] = details
    path.write_text(json.dumps(data, indent=2))


def build_baseline_results(world_id: str, profiles: List[workflow.ProfileSpec]) -> Dict[str, Any]:
    run_id = os.environ.get("SANDBOX_LORE_RUN_ID")
    results: List[Dict[str, Any]] = []
    for spec in profiles:
        for probe in spec.probes:
            results.append(_baseline_for_probe(spec.profile_id, probe))
    return {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "world_id": world_id,
        "run_id": run_id,
        "results": results,
    }


def write_oracle_results(events_path: Path, world_id: str) -> None:
    if not events_path.exists():
        return
    data = json.loads(events_path.read_text())
    results = []
    for row in data:
        callouts = row.get("seatbelt_callouts") or []
        if not callouts:
            continue
        for callout in callouts:
            results.append(
                {
                    "world_id": world_id,
                    "run_id": row.get("run_id"),
                    "expectation_id": row.get("expectation_id"),
                    "operation": callout.get("operation"),
                    "filter_type": callout.get("filter_type"),
                    "filter_type_name": callout.get("filter_type_name"),
                    "argument": callout.get("argument"),
                    "decision": callout.get("decision"),
                    "stage": callout.get("stage"),
                }
            )
    write_json(
        ORACLE_RESULTS,
        {
            "schema_version": ORACLE_SCHEMA_VERSION,
            "world_id": world_id,
            "run_id": os.environ.get("SANDBOX_LORE_RUN_ID"),
            "results": results,
        },
    )


def write_summary(
    world_id: str,
    profiles: List[workflow.ProfileSpec],
    mismatch_summary: Dict[str, Any],
    *,
    status_override: Optional[str] = None,
    dry_run: bool = False,
) -> None:
    expected_profiles = [spec.profile_id for spec in profiles]
    mismatches = mismatch_summary.get("mismatches") or []
    status = status_override or ("ok" if not mismatches else "partial")
    run_id = os.environ.get("SANDBOX_LORE_RUN_ID")
    summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "world_id": world_id,
        "run_id": run_id,
        "status": status,
        "expected_profiles": expected_profiles,
        "mismatch_counts": mismatch_summary.get("counts") or {},
    }
    if dry_run:
        summary["dry_run"] = True
    write_json(SUMMARY_JSON, summary)
    lines = ["# Hardened Runtime Summary", "", f"Status: {status}", ""]
    if mismatches:
        lines.append(f"Mismatches: {len(mismatches)}")
    else:
        lines.append("Mismatches: none")
    SUMMARY_MD.write_text("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run hardened-runtime probes")
    parser.add_argument("--preflight-only", action="store_true", help="Run apply preflight only and exit")
    parser.add_argument("--no-require-clean", action="store_true", help="Allow running outside the launchd clean channel")
    parser.add_argument("--no-seatbelt-callout", action="store_true", help="Disable sandbox_check callout lane")
    parser.add_argument("--dry", action="store_true", help="Validate profiles and gating without running probes")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    require_clean = not args.no_require_clean
    if require_clean and os.environ.get("SANDBOX_LORE_LAUNCHD_CLEAN") != "1" and not args.dry:
        print("[!] hardened-runtime requires the launchd clean channel; use run_via_launchctl.py")
        return 2
    if not args.no_seatbelt_callout:
        os.environ["SANDBOX_LORE_SEATBELT_CALLOUT"] = "1"

    world_id = load_world_id()
    profiles = build_all_profiles(SB_DIR)
    if not profiles:
        print("[!] no hardened-runtime probe families configured")
        return 2
    for spec in profiles:
        for probe in spec.probes:
            op = probe.get("operation") or ""
            if op.startswith("file-"):
                print(f"[!] unexpected VFS probe in hardened-runtime: {op} ({spec.profile_id})")
                return 2

    if args.dry:
        for spec in profiles:
            if not spec.profile_path.exists():
                print(f"[!] missing profile: {spec.profile_id} ({spec.profile_path})")
                return 2
        # Generate an expected matrix for inspection; no probes are run.
        matrix = workflow.build_matrix(world_id, profiles, OUT_DIR / "sb_build")
        write_json(OUT_DIR / "expected_matrix.json", matrix)
        write_summary(world_id, profiles, {"counts": {}, "mismatches": []}, status_override="not_run", dry_run=True)
        return 0

    preflight = run_apply_preflight(world_id)
    write_json(APPLY_PREFLIGHT_OUT, preflight)
    if args.preflight_only:
        return 0 if preflight.get("apply_ok") else 2
    if require_clean and not preflight.get("apply_ok"):
        print("[!] apply preflight failed; refusing to run hardened-runtime")
        return 2

    baseline_doc = build_baseline_results(world_id, profiles)
    write_json(BASELINE_RESULTS, baseline_doc)

    run = workflow.run_profiles(profiles, OUT_DIR, world_id=world_id)
    matrix_path = run.expected_matrix
    runtime_out = run.runtime_results

    if matrix_path.exists():
        (OUT_DIR / "expected_matrix.json").write_text(Path(matrix_path).read_text())
    runtime_results_path = OUT_DIR / "runtime_results.json"
    if runtime_out.exists():
        runtime_results_path.write_text(Path(runtime_out).read_text())

    mismatch_doc = {}
    if run.mismatch_summary:
        mismatch_doc = json.loads(Path(run.mismatch_summary).read_text())
        (OUT_DIR / "mismatch_summary.json").write_text(json.dumps(mismatch_doc, indent=2))

    events_path = OUT_DIR / "runtime_events.normalized.json"
    run_id = os.environ.get("SANDBOX_LORE_RUN_ID")
    if runtime_results_path.exists():
        _annotate_runtime_results(runtime_results_path)
    write_matrix_observations(matrix_path, runtime_results_path, events_path, world_id=world_id, run_id=run_id)

    write_oracle_results(events_path, world_id)
    try:
        mismatch_packets.main()
    except Exception as exc:
        print(f"[!] mismatch packet generation failed: {exc}")
    write_summary(world_id, profiles, mismatch_doc)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
