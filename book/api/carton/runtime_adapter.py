"""
Adapter that lets CARTON-style consumers read runtime cuts and emit
legacy views (runtime_signatures/coverage) without touching experiment
outputs directly.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from book.api import path_utils
from book.api.runtime import story as rt_story

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STORY = ROOT / "book/graph/mappings/runtime_cuts/runtime_story.json"


def load_runtime_story(path: Path | str = DEFAULT_STORY) -> Dict[str, Any]:
    story_path = path_utils.ensure_absolute(path, ROOT)
    if not story_path.exists():
        raise FileNotFoundError(f"runtime story not found at {story_path}")
    return json.loads(story_path.read_text())


def runtime_signatures_view(story_doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Derive a runtime_signatures-like mapping from a runtime story.
    """

    return rt_story.story_to_runtime_signatures(story_doc)


def runtime_coverage_view(story_doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Derive a runtime coverage view (runtime_signatures only) from a runtime story.
    """

    return rt_story.story_to_coverage(story_doc)
