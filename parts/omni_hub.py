"""omni_hub.py — the omni-wheel hub/frame that holds the barrel rollers.
   py cad -> build/omni_hub.stl

Carve-out design: start from a solid blank and SUBTRACT each roller's envelope (the barrel
dilated by a spin clearance), so the rollers are guaranteed to spin free — the pockets are
the rollers plus clearance, by construction. What remains between pockets holds the
off-the-shelf metal pins (tangent, through both flanks of each pocket). Central bore + horn
mount drive it. Reverse-engineered from _omni.py — MEASURE your wheel and set the params.
"""
import math
import os
import sys

import numpy as np
from build123d import *

sys.path.insert(0, os.path.dirname(__file__))
from _omni import (BARREL_MAX, HALF_L, HORN_BC_D, HORN_N, HORN_SCREW, HUB_BORE,  # noqa: E402
                   MOUNT_R, N_ROLLERS, PIN_D, ROLLER_SAMPLES, rho, roller_center)

CLR = 1.0                             # roller spin clearance (pocket = barrel + CLR)
CLEAR_R = MOUNT_R + 3.0               # blank radius: holds pins, stays inside the roller OD
FRAME_H = 2 * BARREL_MAX + 4          # Z height: encloses the roller barrels


def _envelope_roller(clr=CLR):
    """A solid barrel = the roller dilated by clr, used to carve its clearance pocket."""
    zc = HALF_L + clr
    zs = np.linspace(-zc, zc, ROLLER_SAMPLES)
    outer = [(max(0.2, float(rho(z)) + clr), float(z)) for z in zs]
    pts = [(0.2, -zc)] + outer + [(0.2, zc)]
    with BuildPart() as p:
        with BuildSketch(Plane.XZ):
            with BuildLine():
                Polyline(*pts, close=True)
            make_face()
        revolve(axis=Axis.Z)
    return p.part


def _build():
    hub = Cylinder(CLEAR_R, FRAME_H)                   # solid blank, axis Z
    cutter = _envelope_roller()
    for i in range(N_ROLLERS):
        (cx, cy), _, deg = roller_center(i)
        hub -= Pos(cx, cy, 0) * Rot(0, 0, deg) * Rot(90, 0, 0) * cutter   # carve the pocket

    hub -= Cylinder(HUB_BORE / 2, FRAME_H + 2)         # drive bore
    for i in range(HORN_N):                            # horn bolt circle
        a = 2 * math.pi * i / HORN_N
        hub -= Pos((HORN_BC_D / 2) * math.cos(a), (HORN_BC_D / 2) * math.sin(a), 0) * \
            Cylinder(HORN_SCREW / 2, FRAME_H + 2)
    for i in range(N_ROLLERS):                         # tangent pin hole per roller
        (cx, cy), _, deg = roller_center(i)
        hub -= Pos(cx, cy, 0) * Rot(0, 0, deg) * Rot(90, 0, 0) * \
            Cylinder(PIN_D / 2, 2 * (HALF_L + 8))
    return hub


part = _build()   # module-level built solid (repo convention)


if __name__ == "__main__":
    os.makedirs("build", exist_ok=True)
    export_stl(part, "build/omni_hub.stl")
    import trimesh
    m = trimesh.load("build/omni_hub.stl")
    print("omni_hub:", (m.bounds[1] - m.bounds[0]).round(1),
          "bodies:", len(m.split(only_watertight=False)), "watertight:", m.is_watertight)
