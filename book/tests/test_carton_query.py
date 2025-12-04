from book.api.carton import carton_query


def test_profiles_with_operation():
    profiles = carton_query.profiles_with_operation("file-read*")
    assert profiles, "expected at least one profile with file-read*"
    assert "sys:bsd" in profiles


def test_runtime_signature_info():
    info = carton_query.runtime_signature_info("bucket4:v1_read")
    assert info["probes"]
    assert "read_/etc/hosts" in info["probes"]
    assert info["runtime_profile"]


def test_profiles_and_signatures_for_operation():
    info = carton_query.profiles_and_signatures_for_operation("file-read*")
    assert "sys:bsd" in info["system_profiles"]
    assert "bucket4:v1_read" in info["runtime_signatures"]
    counts = info.get("counts") or {}
    assert counts.get("system_profiles", 0) > 0


def test_ops_with_low_coverage_returns_sorted():
    low = carton_query.ops_with_low_coverage(threshold=0)
    assert isinstance(low, list)
    if low:
        total = low[0]["counts"]["system_profiles"] + low[0]["counts"]["runtime_signatures"]
        assert total == min(
            entry["counts"]["system_profiles"] + entry["counts"]["runtime_signatures"] for entry in low
        )
