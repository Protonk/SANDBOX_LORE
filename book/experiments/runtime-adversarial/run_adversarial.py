#!/usr/bin/env python3
"""
Phase 1 adversarial runtime harness.

Builds expected matrices for two families (structural variants, path/literal edges),
compiles SBPL → blob, runs runtime probes via runtime_tools, and emits mismatch summaries.
"""
from __future__ import annotations
import argparse
import ctypes
import ctypes.util
import fcntl
import json
import os
import plistlib
import socket
import socketserver
import errno
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure repository root is on sys.path for `book` imports when run directly.
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from book.api import path_utils
from book.api.runtime_tools import workflow
from book.api.runtime_tools.core import contract as rt_contract
from book.api.runtime_tools.core.models import WORLD_ID
from book.api.runtime_tools.core.normalize import write_matrix_observations

REPO_ROOT = path_utils.find_repo_root(Path(__file__))

BASE_DIR = Path(__file__).resolve().parent
SB_DIR = BASE_DIR / "sb"
BUILD_DIR = SB_DIR / "build"
OUT_DIR = BASE_DIR / "out"
WORLD_PATH = REPO_ROOT / "book" / "world" / "sonoma-14.4.1-23E224-arm64" / "world-baseline.json"
ADVERSARIAL_SUMMARY = REPO_ROOT / "book" / "graph" / "mappings" / "runtime" / "adversarial_summary.json"
APPLY_PREFLIGHT_PROFILE = SB_DIR / "apply_preflight_allow.sb"
APPLY_PREFLIGHT_OUT = OUT_DIR / "apply_preflight.json"
BASELINE_RESULTS = OUT_DIR / "baseline_results.json"
HISTORICAL_EVENTS = OUT_DIR / "historical_runtime_events.json"
HISTORICAL_RESULTS = OUT_DIR / "historical_runtime_results.json"
SANDBOX_RUNNER = REPO_ROOT / "book" / "experiments" / "runtime-checks" / "sandbox_runner"
CODESIGN = Path("/usr/bin/codesign")
LAUNCHCTL = Path("/bin/launchctl")
LOG_CMD = Path("/usr/bin/log")

_LIBPROC = None
_LIBPROC_ERROR = None
_PROC_PIDINFO = None
_PROC_PIDPATH = None

_PROC_PIDTBSDINFO = 3
_MAXCOMLEN = 16


class _ProcBsdInfo(ctypes.Structure):
    _fields_ = [
        ("pbi_flags", ctypes.c_uint32),
        ("pbi_status", ctypes.c_uint32),
        ("pbi_xstatus", ctypes.c_uint32),
        ("pbi_pid", ctypes.c_uint32),
        ("pbi_ppid", ctypes.c_uint32),
        ("pbi_uid", ctypes.c_uint32),
        ("pbi_gid", ctypes.c_uint32),
        ("pbi_ruid", ctypes.c_uint32),
        ("pbi_rgid", ctypes.c_uint32),
        ("pbi_svuid", ctypes.c_uint32),
        ("pbi_svgid", ctypes.c_uint32),
        ("rfu_1", ctypes.c_uint32),
        ("pbi_comm", ctypes.c_char * _MAXCOMLEN),
        ("pbi_name", ctypes.c_char * (2 * _MAXCOMLEN)),
        ("pbi_nfiles", ctypes.c_uint32),
        ("pbi_pgid", ctypes.c_uint32),
        ("pbi_pjobc", ctypes.c_uint32),
        ("e_tdev", ctypes.c_uint32),
        ("e_tpgid", ctypes.c_uint32),
        ("pbi_nice", ctypes.c_int32),
        ("pbi_start_tvsec", ctypes.c_uint64),
        ("pbi_start_tvusec", ctypes.c_uint64),
    ]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def load_world_id() -> str:
    import json

    data = json.loads(WORLD_PATH.read_text())
    return data.get("world_id") or data.get("id", WORLD_ID)

def _mark_file_probe(probes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for probe in probes:
        op = probe.get("operation") or ""
        if isinstance(op, str) and op.startswith("file-"):
            probe.setdefault("driver", "file_probe")
    return probes


def _parent_chain(max_depth: int = 6) -> tuple[List[Dict[str, Any]], str]:
    chain = _libproc_chain(max_depth=max_depth)
    if chain:
        return chain, "libproc"
    return (
        [{"pid": os.getpid(), "ppid": os.getppid(), "command": " ".join(sys.argv)[:200]}],
        "fallback",
    )


_ENTITLEMENTS_CACHE: Dict[str, Dict[str, Any]] = {}


def _extract_plist(text: str) -> Optional[bytes]:
    start = text.find("<?xml")
    if start == -1:
        return None
    end = text.rfind("</plist>")
    if end == -1:
        return None
    return text[start : end + len("</plist>")].encode("utf-8")


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


def _baseline_file_read(path: str) -> Dict[str, Any]:
    record: Dict[str, Any] = {"operation": "file-read*", "target": path}
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError as exc:
        record["status"] = "deny"
        record["errno"] = exc.errno
        record["errno_name"] = errno.errorcode.get(exc.errno)
        record["observed_path_source"] = "unsandboxed_error"
        return record
    try:
        buf = fcntl.fcntl(fd, fcntl.F_GETPATH, b"\0" * 1024)
        observed = buf.split(b"\0", 1)[0].decode("utf-8", errors="replace")
        record["status"] = "allow"
        record["observed_path"] = observed
        record["observed_path_source"] = "unsandboxed_fd_path"
    except OSError as exc:
        record["status"] = "deny"
        record["errno"] = exc.errno
        record["errno_name"] = errno.errorcode.get(exc.errno)
        record["observed_path_source"] = "unsandboxed_error"
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
    return record


def _baseline_network_connect(target: str, timeout: float = 2.0) -> Dict[str, Any]:
    record: Dict[str, Any] = {"operation": "network-outbound", "target": target}
    host = target
    port = None
    if ":" in target:
        host, port_str = target.rsplit(":", 1)
        try:
            port = int(port_str)
        except ValueError:
            port = None
    if port is None:
        record["status"] = "deny"
        record["error"] = "missing_port"
        return record
    try:
        with socket.create_connection((host, port), timeout=timeout):
            record["status"] = "allow"
    except OSError as exc:
        record["status"] = "deny"
        record["errno"] = exc.errno
        record["errno_name"] = errno.errorcode.get(exc.errno)
        record["error"] = str(exc)
    return record


def build_baseline_results(world_id: str, run_id: Optional[str], loopback_targets: List[str]) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    base = _baseline_file_read("/tmp/runtime-adv/edges/okdir/item.txt")
    base.update(
        {
            "name": "baseline:adv:path_edges:allow-subpath",
            "profile_id": "adv:path_edges",
            "probe_name": "allow-subpath",
        }
    )
    results.append(base)
    normalized = _baseline_file_read("/private/tmp/runtime-adv/edges/okdir/item.txt")
    normalized.update(
        {
            "name": "baseline:adv:path_edges:allow-subpath-normalized",
            "profile_id": "adv:path_edges",
            "probe_name": "allow-subpath-normalized",
        }
    )
    results.append(normalized)
    if loopback_targets:
        target = loopback_targets[0]
        net_base = _baseline_network_connect(target)
        net_base.update(
            {
                "name": "baseline:adv:flow_divert_require_all_tcp:tcp-loopback",
                "profile_id": "adv:flow_divert_require_all_tcp",
                "probe_name": "tcp-loopback",
            }
        )
        results.append(net_base)
        net_partial = dict(net_base)
        net_partial.update(
            {
                "name": "baseline:adv:flow_divert_partial_tcp:tcp-loopback",
                "profile_id": "adv:flow_divert_partial_tcp",
                "probe_name": "tcp-loopback",
            }
        )
        results.append(net_partial)
    return {"world_id": world_id, "run_id": run_id, "results": results}


def _truncate_text(text: str, limit: int = 4096) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n[truncated]\n"


def _load_libproc() -> Optional[str]:
    global _LIBPROC, _LIBPROC_ERROR, _PROC_PIDINFO, _PROC_PIDPATH
    if _LIBPROC is not None or _LIBPROC_ERROR is not None:
        return _LIBPROC_ERROR
    lib = ctypes.util.find_library("proc")
    if not lib:
        _LIBPROC_ERROR = "libproc_not_found"
        return _LIBPROC_ERROR
    try:
        _LIBPROC = ctypes.CDLL(lib, use_errno=True)
        _PROC_PIDINFO = _LIBPROC.proc_pidinfo
        _PROC_PIDINFO.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_int]
        _PROC_PIDINFO.restype = ctypes.c_int
        _PROC_PIDPATH = _LIBPROC.proc_pidpath
        _PROC_PIDPATH.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
        _PROC_PIDPATH.restype = ctypes.c_int
        _LIBPROC_ERROR = None
    except Exception as exc:
        _LIBPROC = None
        _PROC_PIDINFO = None
        _PROC_PIDPATH = None
        _LIBPROC_ERROR = str(exc)
    return _LIBPROC_ERROR


def _libproc_pidinfo(pid: int) -> Dict[str, Any]:
    err = _load_libproc()
    if err:
        return {"error": err}
    info = _ProcBsdInfo()
    rc = _PROC_PIDINFO(pid, _PROC_PIDTBSDINFO, 0, ctypes.byref(info), ctypes.sizeof(info))
    if rc <= 0:
        errno = ctypes.get_errno()
        return {"error": "proc_pidinfo_failed", "errno": errno}
    comm = bytes(info.pbi_comm).split(b"\0", 1)[0].decode("utf-8", errors="replace")
    name = bytes(info.pbi_name).split(b"\0", 1)[0].decode("utf-8", errors="replace")
    return {
        "ppid": int(info.pbi_ppid),
        "comm": comm,
        "name": name,
        "pid": int(info.pbi_pid),
    }


def _libproc_pidpath(pid: int) -> Dict[str, Any]:
    err = _load_libproc()
    if err:
        return {"error": err}
    buf = ctypes.create_string_buffer(4096)
    rc = _PROC_PIDPATH(pid, buf, ctypes.sizeof(buf))
    if rc <= 0:
        errno = ctypes.get_errno()
        return {"error": "proc_pidpath_failed", "errno": errno}
    path = buf.value.decode("utf-8", errors="replace")
    return {"path": path}


def _libproc_chain(max_depth: int = 6) -> List[Dict[str, Any]]:
    chain: List[Dict[str, Any]] = []
    pid = os.getpid()
    seen = set()
    for _ in range(max_depth):
        if pid in seen:
            break
        seen.add(pid)
        info = _libproc_pidinfo(pid)
        path_info = _libproc_pidpath(pid)
        entry: Dict[str, Any] = {"pid": pid, "source": "libproc"}
        entry.update(info)
        entry.update(path_info)
        chain.append(entry)
        ppid = info.get("ppid")
        if not isinstance(ppid, int) or ppid <= 0 or ppid == pid:
            break
        pid = ppid
    return chain


def _parse_procinfo(text: str) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if not key or not value:
            continue
        if key in {"sandboxed", "container", "responsible", "responsible path", "job", "label", "path"}:
            parsed[key] = value
        elif "sandbox" in key and "sandboxed" not in parsed:
            parsed["sandboxed"] = value
        elif "container" in key and "container" not in parsed:
            parsed["container"] = value
        elif "responsible" in key and "responsible" not in parsed:
            parsed["responsible"] = value
    return parsed


def _run_launchctl_procinfo(pid: int) -> Dict[str, Any]:
    record: Dict[str, Any] = {"pid": pid, "command": [str(LAUNCHCTL), "procinfo", str(pid)]}
    if not LAUNCHCTL.exists():
        record["status"] = "error"
        record["error"] = "launchctl_missing"
        return record
    try:
        res = subprocess.run(
            [str(LAUNCHCTL), "procinfo", str(pid)],
            capture_output=True,
            text=True,
            timeout=3,
        )
        stdout = res.stdout or ""
        stderr = res.stderr or ""
        combined = stdout + stderr
        denied = "Operation not permitted" in combined or "not permitted" in combined
        record.update(
            {
                "status": "ok" if res.returncode == 0 else "error",
                "returncode": res.returncode,
                "denied": denied,
                "raw": _truncate_text(combined),
                "parsed": _parse_procinfo(combined),
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
        record["status"] = "error"
        record["error"] = "log_missing"
        return record
    try:
        res = subprocess.run(
            record["command"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        combined = (res.stdout or "") + (res.stderr or "")
        denied = "Operation not permitted" in combined or "not permitted" in combined
        record.update(
            {
                "status": "ok" if res.returncode == 0 else "error",
                "returncode": res.returncode,
                "denied": denied,
                "stderr": _truncate_text(res.stderr or ""),
            }
        )
    except subprocess.TimeoutExpired:
        record.update({"status": "error", "error": "timeout"})
    except Exception as exc:
        record.update({"status": "error", "error": str(exc)})
    return record


def _derive_outer_attribution(procinfo: List[Dict[str, Any]], parent_chain: List[Dict[str, Any]]) -> Dict[str, Any]:
    attribution = {"status": "unknown", "tier": "partial", "source": None}
    for entry in procinfo:
        parsed = entry.get("parsed") or {}
        if not isinstance(parsed, dict):
            continue
        sandboxed = parsed.get("sandboxed")
        container = parsed.get("container")
        responsible = parsed.get("responsible") or parsed.get("responsible path")
        label = parsed.get("label") or parsed.get("job")
        if sandboxed or container or responsible or label:
            attribution.update(
                {
                    "status": "observed",
                    "source": "launchctl_procinfo",
                    "sandboxed": sandboxed,
                    "container": container,
                    "responsible": responsible,
                    "job_label": label,
                }
            )
            return attribution
    if len(parent_chain) >= 2:
        launcher = parent_chain[1]
        attribution.update(
            {
                "status": "partial",
                "source": "libproc_parent_chain",
                "launcher": {
                    "pid": launcher.get("pid"),
                    "comm": launcher.get("comm"),
                    "path": launcher.get("path"),
                },
                "notes": "launchctl procinfo unavailable; using parent chain only",
            }
        )
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
    parent_chain, chain_source = _parent_chain()
    run_id = os.environ.get("SANDBOX_LORE_RUN_ID")
    pids = [row.get("pid") for row in parent_chain if isinstance(row, dict)]
    pids = [pid for pid in pids if isinstance(pid, int)]
    procinfo = [_run_launchctl_procinfo(pid) for pid in pids]
    procinfo_requires_root = any(
        isinstance(entry, dict)
        and isinstance(entry.get("raw"), str)
        and "requires root" in entry.get("raw", "").lower()
        for entry in procinfo
    )
    record: Dict[str, Any] = {
        "world_id": world_id,
        "run_id": run_id,
        "profile": path_utils.to_repo_relative(APPLY_PREFLIGHT_PROFILE, repo_root=REPO_ROOT),
        "runner": path_utils.to_repo_relative(SANDBOX_RUNNER, repo_root=REPO_ROOT),
        "parent_chain": parent_chain,
        "parent_chain_source": chain_source,
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
                        "denied": any(entry.get("denied") for entry in procinfo if isinstance(entry, dict)),
                        "requires_root": procinfo_requires_root,
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


def ensure_fixture_files() -> None:
    """Create file fixtures used by probes."""
    struct_root = Path("/tmp/runtime-adv/struct")
    edges_root = Path("/tmp/runtime-adv/edges")

    for path in [
        struct_root / "ok" / "allowed.txt",
        struct_root / "ok" / "deep" / "nested.txt",
        struct_root / "blocked.txt",
        struct_root / "outside.txt",
        edges_root / "a",
        edges_root / "okdir" / "item.txt",
        edges_root / "okdir" / ".." / "blocked.txt",
        Path("/tmp/runtime-adv/alias/allow.txt"),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"runtime-adv fixture for {path}\n")


def start_loopback_server() -> Tuple[socketserver.TCPServer, int]:
    """Start a simple TCP listener on 127.0.0.1 that accepts and replies."""

    class Handler(socketserver.BaseRequestHandler):
        def handle(self) -> None:
            try:
                _ = self.request.recv(16)
                self.request.sendall(b"ok")
            except Exception:
                pass

    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    srv: socketserver.TCPServer = ReusableTCPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    return srv, srv.server_address[1]


def build_families(loopback_targets: List[str]) -> List[workflow.ProfileSpec]:
    probes_common_read = _mark_file_probe(
        [
            {
                "name": "allow-ok-root",
                "operation": "file-read*",
                "target": "/tmp/runtime-adv/struct/ok/allowed.txt",
                "expected": "allow",
            },
        {
            "name": "allow-ok-deep",
            "operation": "file-read*",
            "target": "/tmp/runtime-adv/struct/ok/deep/nested.txt",
            "expected": "allow",
        },
        {
            "name": "deny-blocked",
            "operation": "file-read*",
            "target": "/tmp/runtime-adv/struct/blocked.txt",
            "expected": "deny",
        },
            {
                "name": "deny-outside",
                "operation": "file-read*",
                "target": "/tmp/runtime-adv/struct/outside.txt",
                "expected": "deny",
            },
        ]
    )
    probes_common_write = _mark_file_probe(
        [
            {
                "name": "write-ok-root",
                "operation": "file-write*",
                "target": "/tmp/runtime-adv/struct/ok/allowed.txt",
                "expected": "allow",
            },
        {
            "name": "write-ok-deep",
            "operation": "file-write*",
            "target": "/tmp/runtime-adv/struct/ok/deep/nested.txt",
            "expected": "allow",
        },
        {
            "name": "write-blocked",
            "operation": "file-write*",
            "target": "/tmp/runtime-adv/struct/blocked.txt",
            "expected": "deny",
        },
            {
                "name": "write-outside",
                "operation": "file-write*",
                "target": "/tmp/runtime-adv/struct/outside.txt",
                "expected": "deny",
            },
        ]
    )
    probes_edges_read = _mark_file_probe(
        [
            {
                "name": "allow-tmp",
                "operation": "file-read*",
                "target": "/tmp/runtime-adv/edges/a",
                "expected": "allow",
            },
        {
            "name": "deny-private",
            "operation": "file-read*",
            "target": "/private/tmp/runtime-adv/edges/a",
            "expected": "deny",
        },
        {
            "name": "allow-subpath",
            "operation": "file-read*",
            "target": "/tmp/runtime-adv/edges/okdir/item.txt",
            "expected": "allow",
        },
        {
            "name": "allow-subpath-normalized",
            "operation": "file-read*",
            "target": "/private/tmp/runtime-adv/edges/okdir/item.txt",
            "expected": "deny",
        },
            {
                "name": "deny-dotdot",
                "operation": "file-read*",
                "target": "/tmp/runtime-adv/edges/okdir/../blocked.txt",
                "expected": "deny",
            },
        ]
    )
    probes_edges_write = _mark_file_probe(
        [
            {
                "name": "write-tmp",
                "operation": "file-write*",
                "target": "/tmp/runtime-adv/edges/a",
                "expected": "allow",
            },
        {
            "name": "write-private",
            "operation": "file-write*",
            "target": "/private/tmp/runtime-adv/edges/a",
            "expected": "deny",
        },
        {
            "name": "write-subpath",
            "operation": "file-write*",
            "target": "/tmp/runtime-adv/edges/okdir/item.txt",
            "expected": "allow",
        },
            {
                "name": "write-dotdot",
                "operation": "file-write*",
                "target": "/tmp/runtime-adv/edges/okdir/../blocked.txt",
                "expected": "deny",
            },
        ]
    )

    probes_mach = [
        {
            "name": "allow-cfprefsd",
            "operation": "mach-lookup",
            "target": "com.apple.cfprefsd.agent",
            "expected": "allow",
        },
        {
            "name": "deny-bogus",
            "operation": "mach-lookup",
            "target": "com.apple.sandboxadversarial.fake",
            "expected": "deny",
        },
    ]
    probes_mach_local = [
        {
            "name": "allow-cfprefsd-local",
            "operation": "mach-lookup",
            "target": "com.apple.cfprefsd.agent",
            "expected": "allow",
            "mode": "local",
        },
        {
            "name": "deny-bogus-local",
            "operation": "mach-lookup",
            "target": "com.apple.sandboxadversarial.fake",
            "expected": "deny",
            "mode": "local",
        },
    ]

    probes_net_allow = []
    probes_net_deny = []
    for idx, target in enumerate(loopback_targets or ["127.0.0.1"]):
        name = "tcp-loopback" if idx == 0 else f"tcp-loopback-{idx+1}"
        probes_net_allow.append({"name": name, "operation": "network-outbound", "target": target, "expected": "allow"})
        probes_net_deny.append({"name": name, "operation": "network-outbound", "target": target, "expected": "deny"})

    probes_alias_read = _mark_file_probe(
        [
            {
                "name": "alias-tmp",
                "operation": "file-read*",
                "target": "/tmp/runtime-adv/alias/allow.txt",
                "expected": "allow",
            },
            {
                "name": "alias-private",
                "operation": "file-read*",
                "target": "/private/tmp/runtime-adv/alias/allow.txt",
                "expected": "allow",
            },
        ]
    )

    return [
        workflow.ProfileSpec(
            profile_id="adv:struct_flat",
            profile_path=SB_DIR / "struct_flat.sb",
            probes=probes_common_read + probes_common_write,
            family="structural_variants",
            semantic_group="structural:file-read-subpath",
        ),
        workflow.ProfileSpec(
            profile_id="adv:struct_nested",
            profile_path=SB_DIR / "struct_nested.sb",
            probes=probes_common_read + probes_common_write,
            family="structural_variants",
            semantic_group="structural:file-read-subpath",
        ),
        workflow.ProfileSpec(
            profile_id="adv:path_edges",
            profile_path=SB_DIR / "path_edges.sb",
            probes=probes_edges_read + probes_edges_write,
            family="path_edges",
            semantic_group="paths:literal-vs-normalized",
        ),
        workflow.ProfileSpec(
            profile_id="adv:path_alias",
            profile_path=SB_DIR / "path_alias.sb",
            probes=probes_alias_read,
            family="path_alias",
            semantic_group="paths:alias-canonicalization",
        ),
        workflow.ProfileSpec(
            profile_id="adv:mach_simple_allow",
            profile_path=SB_DIR / "mach_simple_allow.sb",
            probes=probes_mach,
            family="mach_variants",
            semantic_group="mach:global-name-allow",
        ),
        workflow.ProfileSpec(
            profile_id="adv:mach_simple_variants",
            profile_path=SB_DIR / "mach_simple_variants.sb",
            probes=probes_mach,
            family="mach_variants",
            semantic_group="mach:global-name-allow",
        ),
        workflow.ProfileSpec(
            profile_id="adv:mach_local_literal",
            profile_path=SB_DIR / "mach_local_literal.sb",
            probes=probes_mach_local,
            family="mach_local",
            semantic_group="mach:local-name-allow",
        ),
        workflow.ProfileSpec(
            profile_id="adv:mach_local_regex",
            profile_path=SB_DIR / "mach_local_regex.sb",
            probes=probes_mach_local,
            family="mach_local",
            semantic_group="mach:local-name-allow",
        ),
        workflow.ProfileSpec(
            profile_id="adv:net_outbound_allow",
            profile_path=SB_DIR / "net_outbound_allow.sb",
            probes=probes_net_allow,
            family="network",
            semantic_group="network:outbound-allow",
        ),
        workflow.ProfileSpec(
            profile_id="adv:net_outbound_deny",
            profile_path=SB_DIR / "net_outbound_deny.sb",
            probes=probes_net_deny,
            family="network",
            semantic_group="network:outbound-deny",
        ),
        workflow.ProfileSpec(
            profile_id="adv:flow_divert_require_all_tcp",
            profile_path=SB_DIR / "flow_divert_require_all_tcp.sb",
            probes=probes_net_allow,
            family="network",
            semantic_group="network:flow-divert-require-all",
        ),
        workflow.ProfileSpec(
            profile_id="adv:flow_divert_partial_tcp",
            profile_path=SB_DIR / "flow_divert_partial_tcp.sb",
            probes=probes_net_allow,
            family="network",
            semantic_group="network:flow-divert-partial",
        ),
    ]


def update_adversarial_summary(world_id: str, matrix: Dict[str, Any], summary: Dict[str, Any]) -> None:
    rows = {
        "world_id": world_id,
        "profiles": len(matrix.get("profiles") or {}),
        "expectations": sum(len(p.get("probes") or []) for p in (matrix.get("profiles") or {}).values()),
        "mismatch_counts": summary.get("counts") or {},
    }
    write_json(ADVERSARIAL_SUMMARY, rows)

def update_historical_events(events_path: Path, runtime_results: Path) -> bool:
    if not events_path.exists():
        return False
    events = json.loads(events_path.read_text())
    decision_stage = False
    for row in events:
        if not isinstance(row, dict):
            continue
        stage = row.get("failure_stage")
        if stage not in {"apply", "bootstrap", "preflight"}:
            decision_stage = True
            break
    if not decision_stage:
        return False
    HISTORICAL_EVENTS.parent.mkdir(parents=True, exist_ok=True)
    HISTORICAL_RESULTS.parent.mkdir(parents=True, exist_ok=True)
    HISTORICAL_EVENTS.write_text(events_path.read_text())
    HISTORICAL_RESULTS.write_text(runtime_results.read_text())
    return True

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run runtime-adversarial suite")
    parser.add_argument(
        "--require-clean",
        action="store_true",
        help="Require apply preflight success before running the harness.",
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Run apply preflight only and exit.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    world_id = load_world_id()
    ensure_fixture_files()
    preflight = run_apply_preflight(world_id)
    write_json(APPLY_PREFLIGHT_OUT, preflight)
    if args.preflight_only:
        return 0 if preflight.get("apply_ok") else 2
    if args.require_clean and not preflight.get("apply_ok"):
        print("[!] apply preflight failed; refusing to run adversarial harness")
        return 2
    loopback_srvs: List[socketserver.TCPServer] = []
    loopback_targets: List[str] = []
    try:
        srv1, port1 = start_loopback_server()
        loopback_srvs.append(srv1)
        loopback_targets.append(f"127.0.0.1:{port1}")
        srv2, port2 = start_loopback_server()
        loopback_srvs.append(srv2)
        loopback_targets.append(f"127.0.0.1:{port2}")
    except Exception:
        loopback_srvs = []
        loopback_targets = []

    run_id = os.environ.get("SANDBOX_LORE_RUN_ID")
    baseline_doc = build_baseline_results(world_id, run_id, loopback_targets)
    write_json(BASELINE_RESULTS, baseline_doc)

    families = build_families(loopback_targets)
    run = workflow.run_profiles(families, OUT_DIR, world_id=world_id)
    matrix_path = run.expected_matrix
    runtime_out = run.runtime_results

    # Keep compatibility filenames for downstream consumers during transition.
    if matrix_path.exists():
        (OUT_DIR / "expected_matrix.json").write_text(Path(matrix_path).read_text())
    if runtime_out.exists():
        (OUT_DIR / "runtime_results.json").write_text(Path(runtime_out).read_text())
    mismatch_doc = {}
    if run.mismatch_summary:
        mismatch_doc = json.loads(Path(run.mismatch_summary).read_text())
        (OUT_DIR / "mismatch_summary.json").write_text(json.dumps(mismatch_doc, indent=2))
    impact_map = OUT_DIR / "impact_map.json"
    impact_body: Dict[str, Any] = {}
    for mismatch in mismatch_doc.get("mismatches") or []:
        eid = mismatch.get("expectation_id")
        if not eid:
            continue
        entry = {
            "world_id": world_id,
            "profile_id": mismatch.get("profile_id"),
            "operation": mismatch.get("operation"),
            "mismatch_type": mismatch.get("mismatch_type"),
            "notes": mismatch.get("notes"),
            "path": mismatch.get("path"),
        }
        if mismatch.get("violation_summary") == "EPERM":
            entry["tags"] = ["apply_gate"]
        impact_body[eid] = entry
    impact_map.write_text(json.dumps(impact_body, indent=2))

    try:
        events_path = OUT_DIR / "runtime_events.normalized.json"
        run_id = os.environ.get("SANDBOX_LORE_RUN_ID")
        write_matrix_observations(matrix_path, runtime_out, events_path, world_id=world_id, run_id=run_id)
        print(f"[+] wrote normalized events to {events_path}")
        print(f"[+] runtime mapping set under {OUT_DIR / 'runtime_mappings'} -> {run.cut}")
        if update_historical_events(events_path, runtime_out):
            print(f"[+] refreshed historical runtime events -> {HISTORICAL_EVENTS}")
    except Exception as e:
        print(f"[!] failed to normalize runtime events: {e}")

    matrix_doc = json.loads(Path(matrix_path).read_text())
    summary_doc = json.loads((OUT_DIR / "mismatch_summary.json").read_text()) if (OUT_DIR / "mismatch_summary.json").exists() else {}
    update_adversarial_summary(world_id, matrix_doc, summary_doc)
    for srv in loopback_srvs:
        try:
            srv.shutdown()
            srv.server_close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
