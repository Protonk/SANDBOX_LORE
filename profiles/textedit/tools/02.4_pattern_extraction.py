"""
Support tool for Section 2.4 ("What TextEdit shows us about the broader system").

Scaffold only: loads TextEdit's specialized SBPL and outlines pattern extraction
hooks for later narrative about system-wide sandbox structure.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


def extract_common_patterns(sb_text: str) -> Dict[str, object]:
    """
    Identify high-level sandboxing patterns in TextEdit's profile that are
    likely representative of many sandboxed apps, for use in Section 2.4:

    - Generic app container rules
    - Read-only access to system paths (/System, /usr/bin, etc.)
    - Large mach-lookup allowlists
    - Ubiquity/iCloud integration patterns

    TODO: Implement simple pattern scanning / regex-based detection.
    """
    return {
        "status": "TODO",
        "notes": "Detect generic patterns (container, system read-only, mach-lookup).",
        "sample_counts": {"characters": len(sb_text), "lines": sb_text.count("\\n") + 1},
    }


def identify_surprising_or_narrow_rules(sb_text: str) -> Dict[str, object]:
    """
    Identify rules that might be unexpectedly narrow or special-cased, e.g.:

    - Special temporary exceptions (if any remain after specialization)
    - Denies that carve out exceptions within broad allows
    - Mach-lookup or file path rules that hint at system-wide policy
      (e.g., tccd, ocspd, App Store content paths).

    TODO: Implement heuristics for "interesting" patterns.
    """
    return {
        "status": "TODO",
        "notes": "Find narrow/special rules worth highlighting for broader-system lessons.",
        "characters": len(sb_text),
    }


def load_specialized_sbpl() -> str:
    base_dir = Path(__file__).resolve().parent.parent
    sbpl_path = base_dir / "textedit-specialized.sb"
    return sbpl_path.read_text(encoding="utf-8")


def main() -> None:
    sbpl_text = load_specialized_sbpl()
    patterns = extract_common_patterns(sbpl_text)
    surprises = identify_surprising_or_narrow_rules(sbpl_text)

    print(json.dumps({"common_patterns": patterns, "surprises": surprises}, indent=2))


if __name__ == "__main__":
    main()
