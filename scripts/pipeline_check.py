#!/usr/bin/env python3
"""Gate: pipelining lowers per-unit cycle time, and parallel machines scale it."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "orchestration"))
from job import build_pipeline  # noqa: E402
from opgraph import schedule  # noqa: E402


def per_unit(n, capacity):
    _, mk = schedule(build_pipeline(n), capacity)
    return mk / n


def main() -> int:
    single = per_unit(1, {})
    amort8 = per_unit(8, {})
    p1 = per_unit(8, {})
    p2 = per_unit(8, {"printer": 2})

    problems = []
    if not amort8 < single:
        problems.append(f"pipelining did not lower per-unit time ({amort8:.1f} vs {single:.1f})")
    if not p2 < p1:
        problems.append(f"second printer did not scale throughput ({p2:.1f} vs {p1:.1f})")

    print(f"per-unit: 1 unit={single:.1f}s  8 units={amort8:.1f}s  "
          f"8 units/2 printers={p2:.1f}s")
    if problems:
        for p in problems:
            print("FAIL:", p)
        return 1
    print("PASS: pipelining amortizes cycle time; adding a printer scales throughput")
    return 0


if __name__ == "__main__":
    sys.exit(main())
