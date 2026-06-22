"""shear_cam.py — the drive cam (the "build" part).

An eccentric cam on the NEMA17 D-shaft. As the motor turns, the lobe bears on the
blade-arm tail, closing the blade with mechanical advantage over a short stroke;
past top-dead-centre the return spring reopens it. CAM_ECC sets the stroke.

    python parts/shear_cam.py   # via check_parts -> exports/
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build123d import Align, Box, Cylinder, Pos, Rot  # noqa: E402

from _shear import CAM_D, CAM_ECC, CAM_T, SHAFT_D, SHAFT_FLAT  # noqa: E402

C, MN = Align.CENTER, Align.MIN

# egg cam: base disc + an eccentric lobe
part = Cylinder(CAM_D / 2, CAM_T, align=(C, C, MN))
part += Pos(CAM_ECC, 0, 0) * Cylinder(CAM_D / 2 - 1.5, CAM_T, align=(C, C, MN))

# D-shaft bore (Ø SHAFT_D with a flat at SHAFT_FLAT depth)
flat_x = SHAFT_D / 2 - SHAFT_FLAT
d_cut = Cylinder(SHAFT_D / 2, CAM_T + 2, align=(C, C, MN))
d_cut -= Pos(flat_x, 0, -1) * Box(SHAFT_D, SHAFT_D, CAM_T + 4, align=(MN, C, MN))
part -= d_cut

# radial grub-screw hole into the bore (M2.5-ish)
part -= Pos(0, -CAM_D / 2 - 1, CAM_T / 2) * Rot(90, 0, 0) * Cylinder(1.3, CAM_D + 2, align=(C, C, MN))

if __name__ == "__main__":
    from build123d import export_step, export_stl
    os.makedirs("exports", exist_ok=True)
    export_step(part, "exports/shear_cam.step")
    export_stl(part, "exports/shear_cam.stl")
    print("shear_cam:", [round(v, 1) for v in part.bounding_box().size])
