import json

from book.api.carton import carton_query


def test_carton_mini_story_coherence():
    # Discovery
    op_name = next(name for name in carton_query.list_operations() if name.startswith("file-read"))
    profile_id = next(pid for pid in carton_query.list_profiles() if pid.startswith("sys:"))
    filter_name = "path"

    op_story = carton_query.operation_story(op_name)
    profile_story = carton_query.profile_story(profile_id)
    filter_story = carton_query.filter_story(filter_name)

    # Operation counts should match the lengths of the returned lists.
    assert op_story["coverage_counts"]["system_profiles"] == len(op_story["system_profiles"])
    assert op_story["coverage_counts"]["runtime_signatures"] == len(op_story["runtime_signatures"])

    # Profile story should report ops that include the chosen op (when present) and expose runtime signatures.
    op_names_in_profile = {op["name"] for op in profile_story["ops"]}
    if op_name in op_names_in_profile:
        assert profile_story["profile_id"] in op_story["system_profiles"]

    # Filter story is conservative today; ensure its usage_status is in the allowed enum.
    assert filter_story["usage_status"] in {
        "present-in-vocab-only",
        "referenced-in-profiles",
        "referenced-in-runtime",
        "unknown",
    }

    # Round-trip via JSON to ensure shapes are serializable/stable.
    json.dumps({"op": op_story, "profile": profile_story, "filter": filter_story})
