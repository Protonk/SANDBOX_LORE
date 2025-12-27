"""
Paths and shared constants for EntitlementJail tooling.

This module centralizes the repo-local location of EntitlementJail.app and its
embedded helper binaries. Import these paths instead of reconstructing them so
callers remain aligned with the fixed tool bundle layout.
"""

from __future__ import annotations

from pathlib import Path

from book.api import path_utils

# Resolve the fixed, repo-local EntitlementJail app bundle and its helpers.
REPO_ROOT = path_utils.find_repo_root(Path(__file__))
EJ_APP = REPO_ROOT / "book" / "tools" / "entitlement" / "EntitlementJail.app"
EJ = EJ_APP / "Contents" / "MacOS" / "entitlement-jail"
LOG_OBSERVER = EJ_APP / "Contents" / "MacOS" / "sandbox-log-observer"
EJ_RESOURCES = EJ_APP / "Contents" / "Resources"
EJ_EVIDENCE = EJ_RESOURCES / "Evidence"
EJ_EVIDENCE_MANIFEST = EJ_EVIDENCE / "manifest.json"
EJ_EVIDENCE_PROFILES = EJ_EVIDENCE / "profiles.json"
EJ_EVIDENCE_SYMBOLS = EJ_EVIDENCE / "symbols.json"
