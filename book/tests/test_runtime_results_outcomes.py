import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "book" / "experiments" / "runtime-checks" / "out" / "runtime_results.json"


def _load_results():
    assert RESULTS.exists(), "missing runtime_results.json"
    return json.loads(RESULTS.read_text())


def _probe_map(entry):
    return {p["name"]: p for p in entry.get("probes") or []}


def test_bucket_profiles_allow_deny():
    data = _load_results()
    bucket4 = _probe_map(data["bucket4:v1_read"])
    assert bucket4["read_/etc/hosts"]["actual"] == "allow"
    assert bucket4["write_/etc/hosts"]["actual"] == "deny"
    assert bucket4["read_/tmp/foo"]["actual"] == "allow"

    bucket5 = _probe_map(data["bucket5:v11_read_subpath"])
    assert bucket5["read_/tmp/foo"]["actual"] == "allow"
    assert bucket5["read_/tmp/bar"]["actual"] == "deny"
    assert bucket5["write_/tmp/foo"]["actual"] == "deny"


def test_sys_bsd_expected_denies():
    data = _load_results()
    bsd = _probe_map(data["sys:bsd"])
    for name in ["read_/etc/hosts", "write_/etc/hosts", "read_/tmp/foo", "write_/tmp/foo"]:
        assert bsd[name]["actual"] == "deny"


def test_metafilter_any_outcomes():
    data = _load_results()
    meta = _probe_map(data["runtime:metafilter_any"])
    assert meta["read_foo"]["actual"] == "allow"
    assert meta["read_bar"]["actual"] == "allow"
    assert meta["read_other"]["actual"] == "allow"
    assert meta["read_baz"]["actual"] == "deny"
    assert meta["write_baz"]["actual"] == "deny"
