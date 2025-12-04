from book.graph.api import carton_query


def test_profiles_with_operation():
    profiles = carton_query.profiles_with_operation("file-read*")
    assert profiles, "expected at least one profile with file-read*"
    assert "sys:bsd" in profiles


def test_runtime_signature_info():
    info = carton_query.runtime_signature_info("bucket4:v1_read")
    assert info["probes"]
    assert "read_/etc/hosts" in info["probes"]
    assert info["runtime_profile"]
