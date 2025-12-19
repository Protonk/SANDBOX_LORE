"""
Shared runtime helpers for this world.

This package owns the canonical runtime observation shape, scenario ID helpers,
and light-weight loaders/normalizers for runtime results emitted by the
runtime harness. It does not run probes; callers should use
`book.api.runtime_harness.runner` for execution and then normalize results here.
"""

from .events import (
    WORLD_ID,
    RuntimeObservation,
    derive_expectation_id,
    make_scenario_id,
    normalize_runtime_results,
    normalize_from_paths,
    write_normalized_events,
    serialize_observation,
)
from .mappings import (
    RUNTIME_LOG_SCHEMA,
    RUNTIME_MAPPING_SCHEMA,
    append_divergence_annotation,
    build_indexes,
    build_manifest,
    build_op_summaries,
    build_scenario_summaries,
    make_metadata,
    write_events_index,
    write_index_mapping,
    write_manifest,
    write_op_mapping,
    write_per_scenario_traces,
    write_scenario_mapping,
)
from .story import (
    build_runtime_story,
    story_to_coverage,
    story_to_runtime_signatures,
    write_runtime_story,
)
from .pipeline import (
    build_op_summary_from_index,
    generate_runtime_cut,
    load_events_from_index,
    run_from_expected_matrix,
    promote_runtime_cut,
)

__all__ = [
    "WORLD_ID",
    "RuntimeObservation",
    "derive_expectation_id",
    "make_scenario_id",
    "normalize_runtime_results",
    "normalize_from_paths",
    "write_normalized_events",
    "serialize_observation",
    "RUNTIME_LOG_SCHEMA",
    "RUNTIME_MAPPING_SCHEMA",
    "append_divergence_annotation",
    "build_indexes",
    "build_manifest",
    "build_op_summaries",
    "build_scenario_summaries",
    "make_metadata",
    "write_events_index",
    "write_index_mapping",
    "write_manifest",
    "write_op_mapping",
    "write_per_scenario_traces",
    "write_scenario_mapping",
    "build_runtime_story",
    "story_to_coverage",
    "story_to_runtime_signatures",
    "write_runtime_story",
    "build_op_summary_from_index",
    "generate_runtime_cut",
    "load_events_from_index",
    "run_from_expected_matrix",
    "promote_runtime_cut",
]
