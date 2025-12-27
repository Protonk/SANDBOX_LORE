#!/usr/bin/env python3
"""
Promote runtime evidence from promotion packets into runtime mappings.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

from book.api import path_utils
from book.api.runtime_tools.mapping import build as mapping_build

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

import promotion_packets
import generate_runtime_story
import generate_runtime_coverage
import generate_runtime_callout_oracle
import generate_runtime_signatures

RUNTIME_CUTS_ROOT = ROOT / "book" / "graph" / "mappings" / "runtime_cuts"


def build_runtime_cuts(packets: List[promotion_packets.PromotionPacket]) -> None:
    expected_matrix, world_id = promotion_packets.merge_expected_matrices(packets)
    observations = []
    for packet in packets:
        observations.extend(promotion_packets.load_observations(packet))

    cuts_root = path_utils.ensure_absolute(RUNTIME_CUTS_ROOT, ROOT)
    cuts_root.mkdir(parents=True, exist_ok=True)

    traces_dir = cuts_root / "traces"
    events_index, _ = mapping_build.write_traces(observations, traces_dir, world_id=world_id)
    events_index_path = cuts_root / "events_index.json"
    mapping_build.write_events_index(events_index, events_index_path)

    scenario_doc = mapping_build.build_scenarios(observations, expected_matrix, world_id=world_id)
    scenario_path = cuts_root / "scenarios.json"
    mapping_build.write_scenarios(scenario_doc, scenario_path)

    op_doc = mapping_build.build_ops(observations, world_id=world_id)
    op_path = cuts_root / "ops.json"
    mapping_build.write_ops(op_doc, op_path)

    idx_doc = mapping_build.build_indexes(scenario_doc, events_index)
    idx_path = cuts_root / "runtime_indexes.json"
    mapping_build.write_indexes(idx_doc, idx_path)

    manifest_doc = mapping_build.build_manifest(world_id, events_index_path, scenario_path, op_path)
    manifest_path = cuts_root / "runtime_manifest.json"
    mapping_build.write_manifest(manifest_doc, manifest_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote runtime mappings from promotion packets.")
    parser.add_argument("--packets", type=Path, action="append", help="Promotion packet paths")
    args = parser.parse_args()

    packet_paths = args.packets or promotion_packets.DEFAULT_PACKET_PATHS
    packets = promotion_packets.load_packets(packet_paths, allow_missing=True)
    for packet in packets:
        promotion_packets.require_clean_manifest(packet, str(packet.packet_path))

    build_runtime_cuts(packets)
    generate_runtime_story.generate(packet_paths=packet_paths)
    generate_runtime_coverage.generate(packet_paths=packet_paths)
    generate_runtime_callout_oracle.generate(packet_paths=packet_paths)
    generate_runtime_signatures.generate(packet_paths=packet_paths)


if __name__ == "__main__":
    main()
