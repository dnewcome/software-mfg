"""shear_blade_arm.py — the moving lever of the shear (the "build" part).

Pivots on the body pin; carries a bought blade insert at the forward end (bypass:
offset in +Y to pass the fixed blade) and a cam-follower tail at the back that the
cam drives to close the cut. A return spring (not modelled) reopens it.

Bypass edge overlap is schematic in v1 — tuned on the bench against the real blades.

    python parts/shear_blade_arm.py   # via check_parts -> exports/
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build123d import Align, Box, Cylinder, Pos, Rot  # noqa: E402

from _shear import (BLADE_L, BLADE_SCREW, BLADE_T, JAW_H, JAW_LEN, JAW_X0, JAW_Y,  # noqa: E402
                    JAW_Z0, MOTOR_Z, PIVOT_D, PIVOT_X, PIVOT_Z)

C, MN, MX = Align.CENTER, Align.MIN, Align.MAX

ARM_TH = 5.0
ARM_Y = JAW_Y / 2 + 0.5 + ARM_TH / 2     # run alongside the fixed jaw on +Y (bypass)
BLADE_TOP = JAW_Z0 + JAW_H               # z where the moving blade meets the fixed jaw

# pivot hub (cylinder along Y)
part = Pos(PIVOT_X, ARM_Y, PIVOT_Z) * Rot(90, 0, 0) * Cylinder(7, ARM_TH, align=(C, C, C))

# forward bar reaching over the jaw to the blade
fwd_len = (JAW_X0 + JAW_LEN) - PIVOT_X + 2
part += Pos(PIVOT_X, ARM_Y, BLADE_TOP) * Box(fwd_len, ARM_TH, 8, align=(MN, C, MN))

# blade insert pocket on the underside of the forward end + 2 M2 holes
bx = JAW_X0 + JAW_LEN - BLADE_L - 1
part -= Pos(bx, ARM_Y, BLADE_TOP) * Box(BLADE_L, ARM_TH + 1, BLADE_T, align=(MN, C, MN))
for sx in (bx + 4, bx + 11):
    part -= Pos(sx, ARM_Y, BLADE_TOP) * Cylinder(BLADE_SCREW / 2, 9, align=(C, C, MN))

# rear/up tail block up to the cam follower height (cam pushes its -X face)
part += Pos(2, ARM_Y, PIVOT_Z) * Box(PIVOT_X - 2, ARM_TH, (MOTOR_Z + 3) - PIVOT_Z, align=(MN, C, MN))

# pivot bore through the hub
part -= Pos(PIVOT_X, ARM_Y, PIVOT_Z) * Rot(90, 0, 0) * Cylinder(PIVOT_D / 2, ARM_TH + 2, align=(C, C, C))

if __name__ == "__main__":
    from build123d import export_step, export_stl
    os.makedirs("exports", exist_ok=True)
    export_step(part, "exports/shear_blade_arm.step")
    export_stl(part, "exports/shear_blade_arm.stl")
    print("shear_blade_arm:", [round(v, 1) for v in part.bounding_box().size])
