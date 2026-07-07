#!/usr/bin/env python3
"""Gate: the reverse-engineered omni wheel assembles and the rollers spin free.

Grey-box reverse engineering validated by the interference checker (sim/interference.py):
  - both printed parts are single watertight solids;
  - the barrel geometry is self-consistent (validity());
  - N rollers on the hub blend into a continuous OD at R_EFF (the pitch-circle constraint);
  - ZERO solid interference in the assembly — rollers clear the hub AND each other, so they
    can actually rotate (the carve-out hub + tuned pitch guarantee it);
  - the roller bore accepts the off-the-shelf metal pin.
"""

import sys
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "sim"))
sys.path.insert(0, str(ROOT / "parts"))
import interference as ix  # noqa: E402
import _omni as o  # noqa: E402

BUILD = ROOT / "build"


def roller_xform(i):
    (cx, cy), _, deg = o.roller_center(i)
    return (trimesh.transformations.translation_matrix([cx, cy, 0])
            @ trimesh.transformations.rotation_matrix(np.radians(deg), [0, 0, 1])
            @ trimesh.transformations.rotation_matrix(np.radians(90), [1, 0, 0]))


def main() -> int:
    problems = []
    for name in ("omni_roller", "omni_hub"):        # ensure fresh STLs exist
        import importlib
        importlib.import_module("subprocess").run(
            [sys.executable, str(ROOT / "parts" / f"{name}.py")], cwd=ROOT, check=True,
            stdout=importlib.import_module("subprocess").DEVNULL)

    if o.validity():
        problems += [f"geometry: {w}" for w in o.validity()]
    if o.ROLLER_BORE <= o.PIN_D:
        problems.append(f"roller bore {o.ROLLER_BORE} must exceed pin {o.PIN_D}")

    hub = trimesh.load(str(BUILD / "omni_hub.stl"))
    roller = trimesh.load(str(BUILD / "omni_roller.stl"))
    for nm, m in (("hub", hub), ("roller", roller)):
        if not m.is_watertight or len(m.split(only_watertight=False)) != 1:
            problems.append(f"{nm} not a single watertight solid")

    sc = ix.Scene().place("hub", hub, np.eye(4))
    maxr = 0.0
    for i in range(o.N_ROLLERS):
        T = roller_xform(i)
        sc.place(f"roller{i}", roller, T)
        v = trimesh.transform_points(roller.vertices, T)
        maxr = max(maxr, float(np.max(np.hypot(v[:, 0], v[:, 1]))))
    if abs(maxr - o.R_EFF) > 0.4:
        problems.append(f"assembled OD radius {maxr:.2f} != R_EFF {o.R_EFF}")

    inter = sc.interferences()
    if inter:
        problems.append(f"assembly interferes (rollers can't spin): "
                        f"{[(h['pair'], h['volume_mm3']) for h in inter[:4]]}")

    print(f"omni wheel: {o.N_ROLLERS} rollers, OD {2*maxr:.0f}mm, barrel {2*o.BARREL_MAX:.0f}mm, "
          f"pin {o.PIN_D}mm, roller gap {o.ROLLER_GAP_MM}mm")
    print(f"  hub {(hub.bounds[1]-hub.bounds[0]).round(1).tolist()}  "
          f"roller {(roller.bounds[1]-roller.bounds[0]).round(1).tolist()}  (both watertight solids)")
    print(f"  assembly interference: {len(inter)} (0 = rollers spin free), OD radius {maxr:.1f}mm")

    if problems:
        for p in problems:
            print("FAIL:", p)
        return 1
    print("PASS: reverse-engineered omni wheel assembles, rollers clear hub + each other, OD = R_EFF")
    return 0


if __name__ == "__main__":
    sys.exit(main())
