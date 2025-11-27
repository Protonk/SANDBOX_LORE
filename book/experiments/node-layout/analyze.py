#!/usr/bin/env python3
"""
Compile SBPL variants under sb/ and emit a structured summary of modern profile blobs.

Outputs:
- build/*.sb.bin (compiled blobs via libsandbox)
- out/summary.json with per-variant metadata:
  - blob length, op_count, op_table entries
  - section lengths (op_table, nodes, literals/regex)
  - stride stats (tags, remainder, edge in-bounds counts) for strides 8/12/16
  - tail records (last 3 full records at stride=12 plus remainder bytes)
"""

from __future__ import annotations

import ctypes
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any

from book.graph.concepts.validation import profile_ingestion as pi


@dataclass
class SandboxProfile(ctypes.Structure):
    # Mirror libsandbox’s sandbox_profile struct so we can free blobs cleanly.
    _fields_ = [
        ("profile_type", ctypes.c_uint32),
        ("reserved", ctypes.c_uint32),
        ("bytecode", ctypes.c_void_p),
        ("bytecode_length", ctypes.c_size_t),
    ]


def compile_sbpl(src: Path, out: Path) -> bytes:
    """
    Compile an SBPL file via libsandbox and write the resulting blob.

    Returns the raw bytes for downstream slicing.
    """
    # Use the private libsandbox entrypoints to compile the SBPL text.
    lib = ctypes.CDLL("libsandbox.dylib")
    lib.sandbox_compile_string.argtypes = [
        ctypes.c_char_p,
        ctypes.c_uint64,
        ctypes.POINTER(ctypes.c_char_p),
    ]
    lib.sandbox_compile_string.restype = ctypes.POINTER(SandboxProfile)
    lib.sandbox_free_profile.argtypes = [ctypes.POINTER(SandboxProfile)]

    text = src.read_text().encode()
    err = ctypes.c_char_p()
    prof = lib.sandbox_compile_string(text, 0, ctypes.byref(err))
    if not prof:
        detail = err.value.decode() if err.value else "unknown"
        raise RuntimeError(f"compile failed for {src}: {detail}")

    blob = ctypes.string_at(prof.contents.bytecode, prof.contents.bytecode_length)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(blob)

    lib.sandbox_free_profile(prof)
    if err:
        ctypes.CDLL(None).free(err)
    return blob


def stride_stats(nodes: bytes, stride: int) -> Dict[str, Any]:
    """
    Summarize node bytes under a fixed stride guess.

    - records/remainder: how many full stride-sized chunks fit
    - tags: byte0 values observed
    - edges_*: counts of interpreted edges that stay within the node array
    """
    recs = len(nodes) // stride
    rem = len(nodes) % stride
    tags = set()
    edge_in_bounds = 0
    edges_total = 0
    for i in range(0, recs * stride, stride):
        rec = nodes[i : i + stride]
        if not rec:
            continue
        tags.add(rec[0])
        if stride >= 6:
            e1 = int.from_bytes(rec[2:4], "little")
            e2 = int.from_bytes(rec[4:6], "little")
            edges_total += 2
            if e1 * stride < len(nodes):
                edge_in_bounds += 1
            if e2 * stride < len(nodes):
                edge_in_bounds += 1
    return {
        "stride": stride,
        "records": recs,
        "remainder": rem,
        "tags": sorted(tags),
        "edges_in_bounds": edge_in_bounds,
        "edges_total": edges_total,
    }


def tail_records(nodes: bytes, stride: int, count: int = 3) -> Dict[str, Any]:
    """
    Grab the last few stride-aligned records and any remainder bytes.

    Helpful when tail structure diverges from the assumed stride.
    """
    recs = len(nodes) // stride
    tail: List[Dict[str, Any]] = []
    for idx in range(max(0, recs - count), recs):
        rec = nodes[idx * stride : (idx + 1) * stride]
        tag = rec[0]
        e1 = int.from_bytes(rec[2:4], "little")
        e2 = int.from_bytes(rec[4:6], "little")
        lit = int.from_bytes(rec[6:8], "little")
        tail.append(
            {
                "index": idx,
                "tag": tag,
                "edge1": e1,
                "edge2": e2,
                "lit": lit,
                "extra": rec[8:12].hex(),
            }
        )
    remainder = nodes[recs * stride :]
    return {"records": tail, "remainder_hex": remainder.hex()}


def op_entries(blob: bytes, op_count: int) -> List[int]:
    # Preamble heuristic: after 0x10 bytes, assume op_count * u16 entrypoints.
    ops = blob[16 : 16 + op_count * 2]
    return [int.from_bytes(ops[i : i + 2], "little") for i in range(0, len(ops), 2)]


def summarize_variant(src: Path, blob: bytes) -> Dict[str, Any]:
    """
    Parse a compiled blob with the shared ingestion helpers and collect
    easily-computable metadata. This stays deliberately shallow: we do not
    attempt to decode the modern node format here, only to record sizes,
    tag distributions, and tail bytes for later analysis. The intent is to
    give downstream tooling and humans a structured snapshot they can use to
    refine layout hypotheses without re-running compilation.
    """
    header = pi.parse_header(pi.ProfileBlob(bytes=blob, source=src.stem))
    sections = pi.slice_sections(pi.ProfileBlob(bytes=blob, source=src.stem), header)
    op_count = header.operation_count or 0
    summary = {
        "name": src.stem,
        "length": len(blob),
        "format_variant": header.format_variant,
        "op_count": op_count,
        "op_entries": op_entries(blob, op_count),
        "section_lengths": {
            "op_table": len(sections.op_table),
            "nodes": len(sections.nodes),
            "literals": len(sections.regex_literals),
        },
        "stride_stats": [],
        "tail": tail_records(sections.nodes, stride=12),
    }
    for stride in (8, 12, 16):
        summary["stride_stats"].append(stride_stats(sections.nodes, stride))
    return summary


def main() -> None:
    # Walk all SBPL variants under sb/, compile them, and emit a JSON summary.
    root = Path(__file__).parent
    sb_dir = root / "sb"
    build_dir = sb_dir / "build"
    out_dir = root / "out"
    out_dir.mkdir(exist_ok=True)

    summaries: List[Dict[str, Any]] = []
    for sb in sorted(sb_dir.glob("*.sb")):
        blob = compile_sbpl(sb, build_dir / f"{sb.stem}.sb.bin")
        summaries.append(summarize_variant(sb, blob))

    out_path = out_dir / "summary.json"
    out_path.write_text(json.dumps(summaries, indent=2, sort_keys=True))
    print(f"[+] wrote {out_path}")


if __name__ == "__main__":
    main()
