"""shear_body.py — housing for the self-actuated shear (the "build" part).

Carries the coupling mount (top), the fixed jaw + bought-blade pocket (front),
the moving-arm pivot, the NEMA17 motor mount (back face), and the wire guide.
Self-reacting: the fixed jaw and the pivot are both anchored here, so the cut
force stays internal.

    python parts/shear_body.py   # via check_parts -> exports/
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build123d import Align, Box, Cylinder, Pos, Rot  # noqa: E402

from _shear import (BLADE_L, BLADE_SCREW, BLADE_T, BLADE_W, BODY_H, BODY_X, BODY_Y,  # noqa: E402
                    BOLT_CLR, BOLT_R, BORE_D, COUPLING_OD, COUPLING_T, JAW_H, JAW_LEN,
                    JAW_X0, JAW_Y, JAW_Z0, MOTOR_Z, MOUNT_ANGLES, NEMA_BC, NEMA_HOLE,
                    NEMA_PILOT_D, NEMA_SHAFT_CLR, PIVOT_D, PIVOT_X, PIVOT_Z, WIRE_D, pos)

C, MN = Align.CENTER, Align.MIN

# main body block (base at z=0) + coupling plate on top
part = Box(BODY_X, BODY_Y, BODY_H, align=(C, C, MN))
part += Pos(0, 0, BODY_H) * Cylinder(COUPLING_OD / 2, COUPLING_T, align=(C, C, MN))

# central bore + 3 coupling mount holes (down from the top plate)
part -= Pos(0, 0, BODY_H - 2) * Cylinder(BORE_D / 2, COUPLING_T + 6, align=(C, C, MN))
for a in MOUNT_ANGLES:
    x, y = pos(BOLT_R, a)
    part -= Pos(x, y, BODY_H - 2) * Cylinder(BOLT_CLR / 2, COUPLING_T + 6, align=(C, C, MN))

# fixed jaw tongue forward (+X) at the bottom, with a bought-blade pocket + 2 M2
part += Pos(JAW_X0, 0, JAW_Z0) * Box(JAW_LEN, JAW_Y, JAW_H, align=(MN, C, MN))
part -= Pos(JAW_X0 + 5, 0, JAW_Z0 + JAW_H - BLADE_T) * Box(BLADE_L, BLADE_W, BLADE_T + 1, align=(MN, C, MN))
for sx in (JAW_X0 + 9, JAW_X0 + 9 + 7):
    part -= Pos(sx, 0, JAW_Z0 + JAW_H - BLADE_T - 6) * Cylinder(BLADE_SCREW / 2, 8, align=(C, C, MN))

# moving-arm pivot: a Ø(PIVOT_D) bore through the body along Y
part -= Pos(PIVOT_X, 0, PIVOT_Z) * Rot(90, 0, 0) * Cylinder(PIVOT_D / 2, BODY_Y + 4, align=(C, C, C))

# NEMA17 mount on the -Y face: pilot recess + through shaft clearance + 4x M3
face_y = -BODY_Y / 2
part -= Pos(0, face_y - 0.01, MOTOR_Z) * Rot(-90, 0, 0) * Cylinder(NEMA_PILOT_D / 2, 4, align=(C, C, MN))
part -= Pos(0, face_y - 1, MOTOR_Z) * Rot(-90, 0, 0) * Cylinder(NEMA_SHAFT_CLR / 2, BODY_Y + 2, align=(C, C, MN))
for dx in (-NEMA_BC / 2, NEMA_BC / 2):
    for dz in (-NEMA_BC / 2, NEMA_BC / 2):
        part -= Pos(dx, face_y - 1, MOTOR_Z + dz) * Rot(-90, 0, 0) * Cylinder(NEMA_HOLE / 2, 9, align=(C, C, MN))

# wire guide: a bore along Y through the jaw front, at the shear line
part -= Pos(JAW_X0 + JAW_LEN - 5, 0, JAW_Z0 + JAW_H) * Rot(90, 0, 0) * Cylinder(WIRE_D / 2, JAW_Y + 6, align=(C, C, C))

if __name__ == "__main__":
    from build123d import export_step, export_stl
    os.makedirs("exports", exist_ok=True)
    export_step(part, "exports/shear_body.step")
    export_stl(part, "exports/shear_body.stl")
    print("shear_body:", [round(v, 1) for v in part.bounding_box().size])
