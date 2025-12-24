#!/usr/bin/env python3
import argparse
import json
import subprocess
import time
from pathlib import Path
from select import select


def build_predicate(base: str, pid: int | None, deny_only: bool) -> str:
    pred = base
    if pid is not None:
        pred = f"({pred}) && processID == {pid}"
    if deny_only:
        pred = f"({pred}) && eventMessage CONTAINS \"deny\""
    return pred


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="Output NDJSON path")
    ap.add_argument("--duration-s", type=float, default=5.0, help="Capture duration")
    ap.add_argument(
        "--predicate",
        default='sender == "Sandbox"',
        help="log stream predicate",
    )
    ap.add_argument("--pid", type=int, help="Optional PID filter")
    ap.add_argument("--deny-only", action="store_true", help="Filter to deny messages")
    ap.add_argument("--meta-out", help="Optional JSON metadata output path")
    args = ap.parse_args()

    pred = build_predicate(args.predicate, args.pid, args.deny_only)
    cmd = ["/usr/bin/log", "stream", "--style", "json", "--predicate", pred]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "predicate": pred,
        "cmd": cmd,
        "pid": args.pid,
        "deny_only": args.deny_only,
        "duration_s": args.duration_s,
        "t0_ns": time.time_ns(),
    }

    with out_path.open("w", encoding="utf-8") as out_f:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            start = time.monotonic()
            stdout = proc.stdout
            if stdout is None:
                raise RuntimeError("log stream stdout unavailable")
            while True:
                remaining = args.duration_s - (time.monotonic() - start)
                if remaining <= 0:
                    break
                rlist, _, _ = select([stdout], [], [], min(0.2, remaining))
                if not rlist:
                    continue
                line = stdout.readline()
                if not line:
                    break
                out_f.write(line)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                proc.kill()
            meta["t1_ns"] = time.time_ns()
            if proc.stderr is not None:
                meta["stderr"] = proc.stderr.read()
            meta["rc"] = proc.returncode

    if args.meta_out:
        Path(args.meta_out).write_text(json.dumps(meta, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
