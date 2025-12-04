"""
Single entrypoint for validation jobs.

Usage examples:
- python -m book.graph.concepts.validation --all
- python -m book.graph.concepts.validation --tag vocab
- python -m book.graph.concepts.validation --experiment field2
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List

# Ensure repo root on sys.path for book.* imports.
ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from book.graph.concepts.validation import registry

METADATA_PATH = ROOT / "book" / "graph" / "concepts" / "validation" / "out" / "metadata.json"
STATUS_PATH = ROOT / "book" / "graph" / "concepts" / "validation" / "out" / "validation_status.json"
ALLOWED_STATUS = {"ok", "partial", "brittle", "blocked", "skipped"}


def load_host_meta() -> Dict:
    if METADATA_PATH.exists():
        try:
            return json.loads(METADATA_PATH.read_text()).get("os", {})
        except Exception:
            return {}
    return {}


def select_jobs(
    jobs: List[registry.ValidationJob],
    ids: List[str],
    tags: List[str],
    experiments: List[str],
    run_all: bool,
) -> List[registry.ValidationJob]:
    if run_all or (not ids and not tags and not experiments):
        return jobs

    selected: List[registry.ValidationJob] = []
    for job in jobs:
        if ids and job.id not in ids:
            continue
        if tags and not any(
            tag in job.tags or job.id.startswith(f"{tag}:") for tag in tags
        ):
            continue
        if experiments and not any(f"experiment:{exp}" in job.tags for exp in experiments):
            continue
        selected.append(job)
    return selected


def normalize_record(job: registry.ValidationJob, result: Dict, host_meta: Dict) -> Dict:
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    status = result.get("status", "ok")
    if status not in ALLOWED_STATUS:
        status = "blocked"
    record = {
        "job_id": job.id,
        "status": status,
        "host": result.get("host") or host_meta,
        "inputs": job.inputs,
        "outputs": result.get("outputs", job.outputs),
        "timestamp": ts,
        "tags": job.tags,
    }
    if "notes" in result:
        record["notes"] = result["notes"]
    if "metrics" in result:
        record["metrics"] = result["metrics"]
    if "error" in result:
        record["error"] = result["error"]
    return record


def run_job(job: registry.ValidationJob, skip_missing_inputs: bool, host_meta: Dict) -> Dict:
    if skip_missing_inputs and not job.has_inputs():
        return normalize_record(
            job,
            {"status": "skipped", "notes": "inputs missing"},
            host_meta,
        )
    try:
        result = job.runner() or {}
        return normalize_record(job, result, host_meta)
    except Exception as exc:  # pragma: no cover
        return normalize_record(job, {"status": "blocked", "error": f"{exc}"}, host_meta)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="run all registered jobs")
    ap.add_argument("--id", action="append", default=[], help="run a specific job id (repeatable)")
    ap.add_argument("--tag", action="append", default=[], help="select jobs by tag (repeatable)")
    ap.add_argument("--experiment", action="append", default=[], help="select jobs tagged with experiment:<name>")
    ap.add_argument("--skip-missing-inputs", action="store_true", help="skip jobs whose inputs are absent")
    ap.add_argument("--list", action="store_true", help="list available jobs and exit")
    ap.add_argument("--describe", help="show details for a specific job id and exit")
    args = ap.parse_args()

    jobs = registry.load_all_jobs()

    if args.describe:
        job = next((j for j in jobs if j.id == args.describe), None)
        if not job:
            print(f"unknown job id: {args.describe}")
            sys.exit(1)
        print(f"job: {job.id}")
        print(f"tags: {', '.join(job.tags) if job.tags else '-'}")
        print(f"inputs: {job.inputs or '-'}")
        print(f"outputs: {job.outputs or '-'}")
        print(f"description: {job.description or '-'}")
        if job.example_command:
            print(f"example: {job.example_command}")
        return

    if args.list:
        for job in jobs:
            tags = ",".join(job.tags) if job.tags else "-"
            desc = f" – {job.description}" if job.description else ""
            print(f"{job.id} [{tags}]{desc}")
        return

    selected = select_jobs(jobs, args.id, args.tag, args.experiment, args.all)
    if not selected:
        print("No jobs selected; use --all or --list to see options.")
        sys.exit(1)

    host_meta = load_host_meta()
    results = [run_job(job, args.skip_missing_inputs, host_meta) for job in selected]
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "schema": {
            "job_id": "string",
            "status": "ok|partial|brittle|blocked|skipped",
            "host": "object",
            "inputs": "list[str]",
            "outputs": "list[str]",
            "timestamp": "rfc3339",
            "tags": "list[str]",
            "notes": "string?",
            "metrics": "object?",
            "error": "string?",
        },
        "jobs": results,
    }
    STATUS_PATH.write_text(json.dumps(payload, indent=2))

    # Human-friendly summary
    for res in results:
        print(f"{res['job_id']}: {res['status']}")


if __name__ == "__main__":
    main()
