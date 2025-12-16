import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
UNKNOWN_NODES_PATH = ROOT / "book/experiments/field2-filters/out/unknown_nodes.json"

# Stable set of high/unknown field2 payloads on this host baseline.
EXPECTED_UNKNOWN_RAW = {
    2560,   # flow-divert tag0 in require-all socket probes
    3584,   # sample/bsd sentinel tag0
    65535,  # airlock_system_fcntl probe sentinel
    10752,  # airlock tag0 payload
    16660,  # bsd tail tag0
    166,    # airlock tag166/tag1 payload
    165,    # airlock tag166 payload
    174,    # bsd tag26 payload
    170,    # bsd tag26 payload
    115,    # bsd tag26 payload
    109,    # bsd tag26 payload
}


def test_expected_unknown_field2_values_present_and_stable():
    raw = json.loads(UNKNOWN_NODES_PATH.read_text())
    observed = set()
    for entries in raw.values():
        for node in entries:
            observed.add(node["raw"])
    # Guard against accidental loss or drift of known unknowns.
    assert EXPECTED_UNKNOWN_RAW.issubset(
        observed
    ), f"missing expected unknowns: {sorted(EXPECTED_UNKNOWN_RAW - observed)}"
    # Prevent silent introduction of new unknowns; adjust EXPECTED_UNKNOWN_RAW deliberately when warranted.
    assert observed.issubset(
        EXPECTED_UNKNOWN_RAW
    ), f"unexpected new unknowns observed: {sorted(observed - EXPECTED_UNKNOWN_RAW)}"
