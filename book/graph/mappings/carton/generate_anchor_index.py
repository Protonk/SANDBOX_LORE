import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
WORLD_ID = "sonoma-14.4.1-23E224-arm64-dyld-2c0602c5"


def load_json(path: Path):
    return json.loads(path.read_text())


def main():
    anchors_path = ROOT / "book" / "graph" / "mappings" / "anchors" / "anchor_field2_map.json"
    hits_path = ROOT / "book" / "experiments" / "probe-op-structure" / "out" / "anchor_hits.json"
    out_path = ROOT / "book" / "graph" / "mappings" / "carton" / "anchor_index.json"

    anchors_doc = load_json(anchors_path)
    hits_doc = load_json(hits_path)

    # Build a quick lookup of anchor -> observations from anchor_hits.
    anchor_hits = {}
    for profile_name, payload in hits_doc.items():
        for anchor_entry in payload.get("anchors") or []:
            name = anchor_entry.get("anchor")
            if not name:
                continue
            anchor_hits.setdefault(name, []).append((profile_name, anchor_entry))

    anchors = {}
    for anchor, entry in anchors_doc.items():
        if anchor == "metadata":
            continue
        profiles = entry.get("profiles") or {}
        field2_values = set()
        node_indices = set()
        sources = []
        for profile_name, observations in profiles.items():
            sources.append(profile_name)
            for obs in observations or []:
                field2_values.update(obs.get("field2_values") or [])
                node_indices.update(obs.get("node_indices") or [])
        anchors[anchor] = {
            "field2_values": sorted(field2_values),
            "node_indices": sorted(node_indices),
            "profiles": sorted(set(sources)),
            "status": entry.get("status", "partial"),
            # Default to exploratory; callers can down-select to stricter roles later.
            "role": entry.get("role", "exploratory"),
            "sources": sorted(set(sources)),
        }
        if anchor not in anchor_hits:
            anchors[anchor]["warning"] = "anchor not present in anchor_hits; keep partial"

    doc = {
        "metadata": {
            "world_id": anchors_doc.get("metadata", {}).get("world_id", WORLD_ID),
            "status": anchors_doc.get("metadata", {}).get("status", "partial"),
            "inputs": [
                "book/graph/mappings/anchors/anchor_field2_map.json",
                "book/experiments/probe-op-structure/out/anchor_hits.json",
            ],
            "source_jobs": ["experiment:probe-op-structure"],
            "notes": "CARTON-facing anchor → field2 hints. Structural only; roles default to exploratory.",
        },
        "anchors": anchors,
    }

    out_path.write_text(json.dumps(doc, indent=2) + "\n")


if __name__ == "__main__":
    main()
