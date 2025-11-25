"""
Support tool for Section 2.2 ("Profiles, containers, and entitlements in practice").

This script is scaffolding: it loads the specialized SBPL, entitlements, and
container notes so future code can relate them in a single view.
"""
from __future__ import annotations

import json
import plistlib
from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_profile_and_entitlements() -> Tuple[str, Dict[str, Any]]:
    """
    Load the specialized SBPL profile and entitlements for TextEdit.

    Intended use (Section 2.2):
    - Show how the app sandbox profile (application.sb → textedit-specialized.sb),
      entitlements, and container paths fit together.
    """
    base_dir = Path(__file__).resolve().parent.parent
    sbpl_path = base_dir / "textedit-specialized.sb"
    entitlements_path = base_dir / "textedit-entitlements.plist"

    sbpl_text = sbpl_path.read_text(encoding="utf-8")
    with entitlements_path.open("rb") as fh:
        entitlements = plistlib.load(fh)
    return sbpl_text, entitlements


def extract_container_roots() -> Tuple[List[str], int]:
    """
    Parse container-notes.md and/or known patterns to identify the logical
    container roots for TextEdit (Data, Documents, Library, etc.).

    TODO: Implement simple parsing of the notes file and/or embed known
    container path templates.
    """
    base_dir = Path(__file__).resolve().parent.parent
    notes_path = base_dir / "container-notes.md"
    raw_notes = notes_path.read_text(encoding="utf-8") if notes_path.exists() else ""

    placeholder_roots: List[str] = [
        "~/Library/Containers/com.apple.TextEdit/Data",
        "~/Library/Containers/com.apple.TextEdit/Data/Documents",
        "~/Library/Containers/com.apple.TextEdit/Data/Library",
    ]

    return placeholder_roots, len(raw_notes)


def main() -> None:
    sbpl_text, entitlements = load_profile_and_entitlements()
    container_roots, notes_length = extract_container_roots()

    minimal_join = {
        "profile_loaded": bool(sbpl_text),
        "entitlements_keys": sorted(entitlements.keys()),
        "notes_length_chars": notes_length,
        "container_roots": container_roots,
    }
    print(json.dumps(minimal_join, indent=2))


if __name__ == "__main__":
    main()
