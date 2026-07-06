#!/usr/bin/env python3
"""Render the foil former's output: flat stock folded into a stiff profile.

    MUJOCO_GL=osmesa python scripts/foil_former_demo.py

Takes the forward model's 2D folded profile (foil_former.simulate) and extrudes it
along the feed axis into a 3D panel — each straight run of foil becomes a thin
ribbon segment. Shows what the (feed, bend) program actually makes.
"""

import math
import subprocess
import sys
from pathlib import Path

import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "sim"))
import foil_former as ff  # noqa: E402

OUT = ROOT / "exports" / "renders"
W, H = 640, 480
PANEL_W = 0.030          # extrusion depth along feed (m)
VIS_THICK = 0.0004       # visual foil thickness (real ~10um is invisible)
_G = mujoco.mjtGeom


def build(program):
    r = ff.simulate(program)
    pts = np.asarray(r["points"], float) * 1e-3      # mm -> m, in the fold (X,Y) plane
    pts = pts - pts.mean(0)
    spec = mujoco.MjSpec()
    spec.option.gravity = [0, 0, 0]
    wb = spec.worldbody
    wb.add_light(pos=[0.05, -0.1, 0.2], dir=[-0.2, 0.4, -1])
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        d = b - a
        length = float(np.hypot(d[0], d[1]))
        if length < 1e-6:
            continue
        ang = math.atan2(d[1], d[0])
        mid = (a + b) / 2
        g = wb.add_geom()
        g.type = _G.mjGEOM_BOX
        g.size = [length / 2, VIS_THICK / 2, PANEL_W / 2]     # long axis, thin, deep
        g.pos = [float(mid[0]), float(mid[1]), 0.0]
        g.quat = [math.cos(ang / 2), 0, 0, math.sin(ang / 2)]  # rotate about Z (feed)
        g.rgba = [0.82, 0.84, 0.86, 1]                         # aluminum
    return spec.compile(), r


# per-profile camera (distance, azimuth, elevation) so each section reads clearly
CAMS = {
    "channel": (0.09, 50, -20),
    "corrugation": (0.075, 20, -35),
}


def render(program, tag):
    m, r = build(program)
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    renderer = mujoco.Renderer(m, height=H, width=W)
    cam = mujoco.MjvCamera()
    cam.lookat[:] = [0, 0, 0]
    cam.distance, cam.azimuth, cam.elevation = CAMS.get(program, (0.09, 50, -20))
    renderer.update_scene(d, camera=cam)
    OUT.mkdir(parents=True, exist_ok=True)
    png = OUT / f"foil_former_{tag}.png"
    from PIL import Image
    Image.fromarray(renderer.render()).save(png)
    print(f"  {tag}: {r['n_bends']} folds, {r['profile_length']} mm stock, "
          f"overbend {r['max_command']} deg -> {png.name}")


def main() -> int:
    print("foil former renders:")
    for program in ("channel", "corrugation"):
        render(program, program)
    return 0


if __name__ == "__main__":
    sys.exit(main())
