"""
Best-effort decoder for modern sandbox profile blobs.

Focuses on structure: header preamble, op-table entries, node chunks (stride 12),
and literal/regex pool slices. This is heuristic and intended to be version-tolerant.
"""

from __future__ import annotations

import string
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


PRINTABLE = set(bytes(string.printable, "ascii"))


@dataclass
class DecodedProfile:
    format_variant: str
    preamble_words: List[int]
    op_count: Optional[int]
    op_table: List[int]
    nodes: List[Dict[str, Any]]
    literal_pool: bytes
    literal_strings: List[str]
    sections: Dict[str, int]


def _read_preamble(data: bytes) -> List[int]:
    words = []
    for i in range(0, min(len(data), 16), 2):
        words.append(int.from_bytes(data[i : i + 2], "little"))
    return words


def _guess_op_count(words: List[int]) -> Optional[int]:
    if len(words) < 2:
        return None
    maybe = words[1]
    if 0 < maybe < 4096:
        return maybe
    return None


def _scan_literal_start(data: bytes, start: int) -> int:
    """Find onset of mostly-printable tail; conservative if none found."""
    window = 64
    threshold = 0.7
    for i in range(start, len(data)):
        chunk = data[i : min(len(data), i + window)]
        if not chunk:
            continue
        printable = sum(1 for b in chunk if b in PRINTABLE or b == 0x00)
        if printable / len(chunk) >= threshold:
            return i
    return len(data)


def _parse_op_table(data: bytes) -> List[int]:
    return [int.from_bytes(data[i : i + 2], "little") for i in range(0, len(data), 2)]


def _parse_nodes_stride12(data: bytes) -> List[Dict[str, Any]]:
    nodes: List[Dict[str, Any]] = []
    for off in range(0, len(data), 12):
        chunk = data[off : off + 12]
        if len(chunk) < 12:
            break
        fields = [int.from_bytes(chunk[i : i + 2], "little") for i in range(0, 12, 2)]
        nodes.append({"offset": off, "tag": fields[0], "fields": fields[1:], "hex": chunk.hex()})
    return nodes


def _extract_strings(buf: bytes, min_len: int = 4) -> List[str]:
    """Pull out printable runs as strings; simple heuristic to aid orientation."""
    out: List[str] = []
    cur: List[int] = []
    for b in buf:
        if b in PRINTABLE and b != 0x00:
            cur.append(b)
        else:
            if len(cur) >= min_len:
                out.append(bytes(cur).decode("ascii", errors="ignore"))
            cur = []
    if len(cur) >= min_len:
        out.append(bytes(cur).decode("ascii", errors="ignore"))
    return out


def decode_profile(data: bytes) -> DecodedProfile:
    preamble = _read_preamble(data)
    op_count = _guess_op_count(preamble)
    op_table_len = (op_count or 0) * 2
    op_table_start = 16
    op_table_end = min(len(data), op_table_start + op_table_len)
    op_table_bytes = data[op_table_start:op_table_end]

    nodes_start = op_table_end
    literal_start = _scan_literal_start(data, nodes_start)
    nodes_bytes = data[nodes_start:literal_start]
    literal_pool = data[literal_start:]

    decoded = DecodedProfile(
        format_variant="modern-heuristic",
        preamble_words=preamble,
        op_count=op_count,
        op_table=_parse_op_table(op_table_bytes),
        nodes=_parse_nodes_stride12(nodes_bytes),
        literal_pool=literal_pool,
        literal_strings=_extract_strings(literal_pool),
        sections={
            "op_table": len(op_table_bytes),
            "nodes": len(nodes_bytes),
            "literal_pool": len(literal_pool),
        },
    )

    return decoded


def decode_profile_dict(data: bytes) -> Dict[str, Any]:
    """Dict wrapper for JSON serialization."""
    d = decode_profile(data)
    return {
        "format_variant": d.format_variant,
        "preamble_words": d.preamble_words,
        "op_count": d.op_count,
        "op_table": d.op_table,
        "nodes": d.nodes,
        "literal_strings": d.literal_strings,
        "sections": d.sections,
    }
