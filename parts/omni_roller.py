"""omni_roller.py — one barrel roller of the reverse-engineered omni wheel.
   py cad -> build/omni_roller.stl

Print in TPU (grip + compliance); it spins on an off-the-shelf metal dowel pin (bore >
pin). The outer surface follows rho(z) = R_EFF - hypot(MOUNT_R, z) so N of these blend into
a continuous round OD. Revolve the barrel profile about its own (tangent) axis.
"""
import os
import sys

import numpy as np
from build123d import *

sys.path.insert(0, os.path.dirname(__file__))
from _omni import HALF_L, ROLLER_BORE, ROLLER_SAMPLES, rho  # noqa: E402


def _build():
    zs = np.linspace(-HALF_L, HALF_L, ROLLER_SAMPLES)
    outer = [(float(rho(z)), float(z)) for z in zs]        # (radius X, axial Z)
    br = ROLLER_BORE / 2
    pts = [(br, -HALF_L)] + outer + [(br, HALF_L)]         # close along the inner bore wall
    with BuildPart() as p:
        with BuildSketch(Plane.XZ):
            with BuildLine():
                Polyline(*pts, close=True)
            make_face()
        revolve(axis=Axis.Z)
    return p.part


part = _build()   # module-level built solid (repo convention)


if __name__ == "__main__":
    os.makedirs("build", exist_ok=True)
    export_stl(part, "build/omni_roller.stl")
    import trimesh
    m = trimesh.load("build/omni_roller.stl")
    print("omni_roller:", (m.bounds[1] - m.bounds[0]).round(1),
          "bodies:", len(m.split(only_watertight=False)), "watertight:", m.is_watertight)
