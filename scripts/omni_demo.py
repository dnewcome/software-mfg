#!/usr/bin/env python3
"""Assemble the reverse-engineered omni wheel (hub + N rollers on pins) into one mesh for
viewing. -> build/omni_assembly.stl (+ a bounds print). Rollers are placed on their tangent
axes; the metal pins are shown as thin cylinders."""
import sys
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "parts"))
import _omni as o  # noqa: E402
from omni_check import roller_xform  # noqa: E402

BUILD = ROOT / "build"


def main():
    import subprocess
    for name in ("omni_roller", "omni_hub"):
        subprocess.run([sys.executable, str(ROOT / "parts" / f"{name}.py")], cwd=ROOT,
                       check=True, stdout=subprocess.DEVNULL)
    hub = trimesh.load(str(BUILD / "omni_hub.stl"))
    roller = trimesh.load(str(BUILD / "omni_roller.stl"))
    parts = [hub]
    for i in range(o.N_ROLLERS):
        r = roller.copy(); r.apply_transform(roller_xform(i)); parts.append(r)
        (cx, cy), _, deg = o.roller_center(i)                       # the metal pin
        pin = trimesh.creation.cylinder(radius=o.PIN_D / 2, height=2 * o.HALF_L + 6)
        pin.apply_transform(trimesh.transformations.translation_matrix([cx, cy, 0])
                            @ trimesh.transformations.rotation_matrix(np.radians(deg), [0, 0, 1])
                            @ trimesh.transformations.rotation_matrix(np.radians(90), [1, 0, 0]))
        parts.append(pin)
    asm = trimesh.util.concatenate(parts)
    out = BUILD / "omni_assembly.stl"
    asm.export(str(out))
    print(f"omni_assembly -> {out}  OD {2*o.R_EFF:.0f}mm, {o.N_ROLLERS} rollers + pins, "
          f"bbox {(asm.bounds[1]-asm.bounds[0]).round(1).tolist()}")


if __name__ == "__main__":
    main()
