import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_IR = ROOT / "book" / "graph" / "concepts" / "validation" / "out" / "experiments" / "runtime-checks" / "runtime_results.normalized.json"
GOLDEN = {
    "bucket4:v1_read",
    "bucket5:v11_read_subpath",
    "runtime:metafilter_any",
    "runtime:strict_1",
    "sys:bsd",
    "sys:airlock",
}


def _load_ir():
    assert RUNTIME_IR.exists(), "missing normalized runtime IR"
    data = json.loads(RUNTIME_IR.read_text())
    return data.get("events") or [], (data.get("expected_matrix") or {}).get("profiles", {})


def _probe_map(events, profile_id):
    out = {}
    for ev in events:
        if ev.get("profile_id") != profile_id:
            continue
        name = ev.get("probe_name")
        if name:
            out[name] = ev
    return out


def test_golden_presence():
    events, matrix = _load_ir()
    assert GOLDEN.issubset(matrix.keys()), "golden profiles missing from expected_matrix"
    present = {e.get("profile_id") for e in events}
    assert GOLDEN.issubset(present), "golden profiles missing from runtime_results"


def test_bucket_profiles_allow_deny():
    data, _ = _load_ir()
    bucket4 = _probe_map(data, "bucket4:v1_read")
    assert bucket4["read_/etc/hosts"]["actual"] == "allow"
    assert bucket4["write_/etc/hosts"]["actual"] == "deny"
    assert bucket4["read_/tmp/foo"]["actual"] == "allow"

    bucket5 = _probe_map(data, "bucket5:v11_read_subpath")
    assert bucket5["read_/tmp/foo"]["actual"] == "allow"
    assert bucket5["read_/tmp/bar"]["actual"] == "deny"
    assert bucket5["write_/tmp/foo"]["actual"] == "deny"


def test_sys_bsd_expected_denies():
    data, _ = _load_ir()
    bsd = _probe_map(data, "sys:bsd")
    for name in ["read_/etc/hosts", "write_/etc/hosts", "read_/tmp/foo", "write_/tmp/foo"]:
        assert bsd[name]["actual"] == "deny"


def test_sys_airlock_expected_fail():
    data, _ = _load_ir()
    airlock = _probe_map(data, "sys:airlock")
    # All probes should fail due to sandbox_init EPERM.
    for probe in airlock.values():
        assert probe["violation_summary"] == "EPERM"
        assert probe["actual"] == "deny"


def test_metafilter_any_outcomes():
    data, _ = _load_ir()
    meta = _probe_map(data, "runtime:metafilter_any")
    assert meta["read_foo"]["actual"] == "allow"
    assert meta["read_bar"]["actual"] == "allow"
    assert meta["read_other"]["actual"] == "allow"
    assert meta["read_baz"]["actual"] == "deny"
    assert meta["write_baz"]["actual"] == "deny"


def test_strict_profile_outcomes():
    data, _ = _load_ir()
    strict = _probe_map(data, "runtime:strict_1")
    assert strict["read_ok"]["actual"] == "allow"
    assert strict["write_ok"]["actual"] == "allow"
    assert strict["read_hosts"]["actual"] == "deny"
    assert strict["write_hosts"]["actual"] == "deny"
