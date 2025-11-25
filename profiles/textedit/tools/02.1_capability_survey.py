"""
Support tool for Section 2.1 ("What TextEdit is allowed to do").

This is a scaffold, not a full analyzer. It wires up entitlement/profile loading
so later work can classify TextEdit's visible capabilities.
"""
from __future__ import annotations

import json
import plistlib
from pathlib import Path
from typing import Any, Dict


def load_inputs() -> tuple[Dict[str, Any], str]:
    """
    Load the entitlements plist and specialized SBPL text for TextEdit.

    Returns:
        entitlements: Parsed plist as a dictionary.
        sbpl_text: Raw SBPL string from textedit-specialized.sb.
    """
    base_dir = Path(__file__).resolve().parent.parent
    entitlements_path = base_dir / "textedit-entitlements.plist"
    sbpl_path = base_dir / "textedit-specialized.sb"

    with entitlements_path.open("rb") as fh:
        entitlements = plistlib.load(fh)

    sbpl_text = sbpl_path.read_text(encoding="utf-8")
    return entitlements, sbpl_text


def summarize_entitlements(entitlements: dict) -> dict:
    """
    Given the entitlements dict for TextEdit, return a coarse summary of
    visible capabilities (e.g., printing, user-selected file access,
    ubiquity/iCloud presence) to support Section 2.1 ("What TextEdit is
    allowed to do").
    TODO: Implement actual grouping and human-readable labels.
    """
    return {
        "status": "TODO",
        "notes": "Group entitlements into capability buckets (printing, files, iCloud).",
        "entitlement_keys_seen": sorted(entitlements.keys()),
    }


def summarize_specialized_sbpl(sb_text: str) -> dict:
    """
    Inspect textedit-specialized.sb and derive a coarse summary of
    allowed/denied areas (filesystem, network, IPC) to cross-check
    expectations from entitlements for Section 2.1.
    TODO: Implement simple pattern matching over SBPL.
    """
    return {
        "status": "TODO",
        "notes": "Scan SBPL for allow/deny patterns (filesystem, network, mach-lookup).",
        "character_count": len(sb_text),
        "lines": sb_text.count("\n") + 1,
    }


def main() -> None:
    entitlements, sbpl_text = load_inputs()
    entitlement_summary = summarize_entitlements(entitlements)
    sbpl_summary = summarize_specialized_sbpl(sbpl_text)

    placeholder_output = {
        "entitlements": entitlement_summary,
        "sbpl": sbpl_summary,
    }
    print(json.dumps(placeholder_output, indent=2))


if __name__ == "__main__":
    main()
