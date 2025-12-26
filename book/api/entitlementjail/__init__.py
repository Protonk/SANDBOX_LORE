"""
EntitlementJail tooling surface (stable API exports).

Re-exports the small, stable API used by experiments and tooling.
"""

from book.api.entitlementjail.cli import (
    WORLD_ID,
    bundle_evidence,
    extract_file_path,
    extract_profile_bundle_id,
    extract_tmp_dir,
    parse_probe_catalog,
    run_cmd,
    run_matrix_group,
    run_xpc,
    write_json,
)
from book.api.entitlementjail.paths import EJ, EJ_APP, LOG_OBSERVER, REPO_ROOT
from book.api.entitlementjail.wait import run_probe_wait, run_wait_xpc

__all__ = [
    "EJ",
    "EJ_APP",
    "LOG_OBSERVER",
    "REPO_ROOT",
    "WORLD_ID",
    "bundle_evidence",
    "extract_file_path",
    "extract_profile_bundle_id",
    "extract_tmp_dir",
    "parse_probe_catalog",
    "run_cmd",
    "run_matrix_group",
    "run_probe_wait",
    "run_wait_xpc",
    "run_xpc",
    "write_json",
]
