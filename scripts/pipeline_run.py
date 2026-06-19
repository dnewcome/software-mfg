#!/usr/bin/env python3
"""Multi-unit production pipeline: show per-unit cycle time dropping + scaling.

Schedules N units sharing the cells, then shows that adding a second printer
(the bottleneck) scales throughput.

    python scripts/pipeline_run.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "orchestration"))
from job import build_pipeline  # noqa: E402
from opgraph import ascii_gantt, schedule  # noqa: E402


def row(n, capacity):
    _, mk = schedule(build_pipeline(n), capacity)
    per_unit = mk / n
    return mk, per_unit, 3600.0 / per_unit


def main() -> int:
    print("PRODUCTION PIPELINE — amortized per-unit cycle time\n")
    print(f"{'units':>5} {'makespan':>9} {'per-unit':>9} {'units/hr':>9}   (1 printer)")
    for n in (1, 2, 3, 5, 8, 12):
        mk, per, thr = row(n, {})
        print(f"{n:5d} {mk:8.0f}s {per:8.1f}s {thr:8.1f}")

    print("\nadd a second printer (the bottleneck resource):")
    print(f"{'units':>5} {'1 printer':>11} {'2 printers':>12} {'speedup':>9}")
    for n in (3, 5, 8, 12):
        _, p1, t1 = row(n, {})
        _, p2, t2 = row(n, {"printer": 2})
        print(f"{n:5d} {p1:9.1f}s/u {p2:10.1f}s/u {t2 / t1:8.2f}x")

    print("\nGantt — 3 units, 1 printer (note units pipelining on the printer):\n")
    sched, mk = schedule(build_pipeline(3), {})
    print(ascii_gantt(sched, mk, width=60))
    return 0


if __name__ == "__main__":
    sys.exit(main())
