"""Time `folio check` on a library, and summarise the timings.

    python3 docs/tools/check_timing.py measure --arm docs --library docs --runs 10 --out docs/assets/data/check-timings.csv
    python3 docs/tools/check_timing.py summarise docs/assets/data/check-timings.csv --arm docs

`measure` runs `folio check` the given number of times, after one untimed warm-up
run, and appends one row per run: the arm, the run number, the wall-clock seconds
and the number of documents the gate reported. It refuses to record a run whose
gate did not pass. `summarise` prints the median for one arm, as
"median <s> s over <n> runs", the form a result records.
"""

from __future__ import annotations

import argparse
import csv
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

FIELDS = ["arm", "run", "seconds", "documents"]


def run_check(library: Path) -> tuple[float, int]:
    start = time.perf_counter()
    proc = subprocess.run([sys.executable, "-m", "folio", "check"], cwd=library, capture_output=True, text=True)
    seconds = time.perf_counter() - start
    if proc.returncode != 0:
        sys.exit(f"folio check failed in {library}; nothing recorded:\n{proc.stdout}{proc.stderr}")
    found = re.search(r"folio check: (\d+) documents", proc.stdout + proc.stderr)
    if not found:
        sys.exit(f"could not read the document count from folio check's output:\n{proc.stdout}{proc.stderr}")
    return seconds, int(found.group(1))


def measure(args: argparse.Namespace) -> None:
    library = Path(args.library)
    run_check(library)  # warm-up, not recorded
    out = Path(args.out)
    new_file = not out.exists()
    with out.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        for n in range(1, args.runs + 1):
            seconds, documents = run_check(library)
            writer.writerow({"arm": args.arm, "run": n, "seconds": f"{seconds:.3f}", "documents": documents})
    print(f"recorded {args.runs} runs of arm {args.arm} in {out}")


def summarise(args: argparse.Namespace) -> None:
    with open(args.csv, newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["arm"] == args.arm]
    if not rows:
        sys.exit(f"no rows for arm {args.arm} in {args.csv}")
    median = statistics.median(float(row["seconds"]) for row in rows)
    print(f"median {median:.2f} s over {len(rows)} runs")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="command", required=True)
    m = sub.add_parser("measure")
    m.add_argument("--arm", required=True)
    m.add_argument("--library", required=True)
    m.add_argument("--runs", type=int, default=10)
    m.add_argument("--out", required=True)
    m.set_defaults(func=measure)
    s = sub.add_parser("summarise")
    s.add_argument("csv")
    s.add_argument("--arm", required=True)
    s.set_defaults(func=summarise)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
