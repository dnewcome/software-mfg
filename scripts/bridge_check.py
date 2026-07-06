#!/usr/bin/env python3
"""Gate: the so101-lab bridge resolves a motion backend and solves a toolpath.

Validates the compose-by-reference bridge and its fallback: whichever backend is live
(so101-lab Placo if its venv+URDF are set up, else the built-in IK), a small path around
the datum must solve to a reachable joint trajectory. Passes standalone (built-in
fallback) and lights up Placo automatically when the hardware cell is provisioned.
"""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sim"))
from bridge import probe, solve_path, status  # noqa: E402
from workcell import DATUM_POS  # noqa: E402


def main() -> int:
    targets = [tuple(DATUM_POS + np.array([dx, 0.0, 0.0])) for dx in (-0.02, 0.0, 0.02)]
    r = solve_path(targets)
    p = probe()
    problems = []

    if len(r["waypoints"]) != len(targets):
        problems.append(f"expected {len(targets)} waypoints, got {len(r['waypoints'])}")
    if r["backend"] not in ("placo", "builtin"):
        problems.append(f"unknown backend {r['backend']!r}")
    if not r["waypoints"] or len(r["waypoints"][0]["q"]) < 5:
        problems.append("solver returned no joint angles")
    if r["max_err_mm"] >= 5.0:
        problems.append(f"toolpath not reachable ({r['max_err_mm']}mm residual)")

    print(status())
    print(f"solved {len(r['waypoints'])} waypoints via {r['backend'].upper()} | "
          f"max residual {r['max_err_mm']}mm")
    print(f"  {r['status']}")
    if problems:
        for pr in problems:
            print("FAIL:", pr)
        return 1
    print("PASS: bridge resolves a motion backend and solves a reachable toolpath "
          "(Placo when so101-lab is provisioned, else built-in)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
