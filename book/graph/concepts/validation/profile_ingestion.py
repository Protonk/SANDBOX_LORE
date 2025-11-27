"""
Minimal, version-tolerant profile ingestion helpers.

This is intentionally light: it provides a stable interface (`parse_header`,
`slice_sections`) that the examples can call without depending on a specific
format variant. Where possible, it recognizes the early decision-tree layout;
otherwise it treats the blob as an opaque modern/unknown format and returns
placeholder counts while still letting callers inspect byte ranges.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ProfileBlob:
    bytes: bytes
    source: str


@dataclass
class Header:
    format_variant: str
    operation_count: Optional[int]
    node_count: Optional[int]
    regex_count: Optional[int]
    raw_length: int


@dataclass
class Sections:
    op_table: bytes
    nodes: bytes
    regex_literals: bytes


def _is_legacy_decision_tree(blob: bytes) -> bool:
    """Heuristic: early format uses u16 re_table_offset (8-byte words) + u8 count."""
    if len(blob) < 4:
        return False
    re_offset_words = int.from_bytes(blob[0:2], "little")
    re_offset_bytes = re_offset_words * 8
    if re_offset_bytes <= 4 or re_offset_bytes > len(blob):
        return False
    # op_table fills the gap between header (4 bytes) and regex table
    return (re_offset_bytes - 4) % 2 == 0


def parse_header(blob: ProfileBlob) -> Header:
    data = blob.bytes
    if _is_legacy_decision_tree(data):
        re_offset_words = int.from_bytes(data[0:2], "little")
        re_offset_bytes = re_offset_words * 8
        re_count = data[2]
        op_table_len = re_offset_bytes - 4
        op_count = op_table_len // 2 if op_table_len >= 0 else None
        return Header(
            format_variant="legacy-decision-tree",
            operation_count=op_count,
            node_count=None,
            regex_count=re_count,
            raw_length=len(data),
        )
    # Heuristic for modern graph-based blobs compiled by libsandbox:
    # - first 16 bytes often contain small u16 fields; the second word usually
    #   matches the number of operations (count of op-table entries).
    # - op table appears immediately after this 16-byte preamble as u16
    #   indices into the node array.
    op_count: Optional[int] = None
    if len(data) >= 18:
        words = [int.from_bytes(data[i : i + 2], "little") for i in range(0, 16, 2)]
        maybe_op = words[1]
        if 0 < maybe_op < 2048:
            op_count = maybe_op
    return Header(
        format_variant="modern-heuristic",
        operation_count=op_count,
        node_count=None,
        regex_count=None,
        raw_length=len(data),
    )


def slice_sections(blob: ProfileBlob, header: Header) -> Sections:
    data = blob.bytes
    if header.format_variant == "legacy-decision-tree":
        re_offset_bytes = int.from_bytes(data[0:2], "little") * 8
        op_table = data[4:re_offset_bytes]
        nodes = b""  # legacy handlers are embedded; keep them in regex_literals below
        regex_literals = data[re_offset_bytes:]
        return Sections(op_table=op_table, nodes=nodes, regex_literals=regex_literals)
    # Modern heuristic: treat bytes 0x10..(0x10 + op_count*2) as op-table.
    op_table_len = 0
    if header.operation_count:
        op_table_len = header.operation_count * 2
    op_table_start = 16
    op_table_end = min(len(data), op_table_start + op_table_len)
    op_table = data[op_table_start:op_table_end]

    # Attempt to split node area vs literal/regex pool by looking for the onset
    # of mostly-printable data near the tail. This is intentionally conservative;
    # if no printable run is found, treat the whole remainder as nodes.
    def find_literal_start(buf: bytes) -> int:
        window = 64
        threshold = 0.7
        for i in range(op_table_end, len(buf)):
            chunk = buf[i : min(len(buf), i + window)]
            if not chunk:
                continue
            printable = sum(
                1
                for b in chunk
                if b == 0x00 or 32 <= b <= 126
            )
            if printable / len(chunk) >= threshold:
                return i
        return len(buf)

    literal_start = find_literal_start(data)
    nodes = data[op_table_end:literal_start]
    regex_literals = data[literal_start:]
    return Sections(op_table=op_table, nodes=nodes, regex_literals=regex_literals)
