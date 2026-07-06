"""foil_lom.py — a layer-forming 3D printer that builds solids from aluminum foil.

Laminated Object Manufacturing (LOM), foil edition: build a solid by stacking
foil layers, bonding each to the stack, and cutting its cross-section contour —
repeat up the Z axis. This is real (Mcor did it with paper; Fabrisonic ultrasonically
welds metal foil into fully-dense parts); the twist here is *common ~10um foil*.

The "program" is a SLICE STACK of a target solid — the direct analog of the wire
bender's bend program or the feature-IR: a CAD solid sliced into contours, each a
(feed foil, bond, cut) op the op-graph schedules. The dominant, uncomfortable fact
this planner surfaces: foil is THIN. A 10um layer means ~100 layers per millimetre,
so a small part is thousands of layers — the throughput reality, reported honestly
rather than hidden.

Target solids are analytic solids-of-revolution (radius as a function of height) so
the planner needs no CAD backend; swap in a sliced build123d/STL contour later.
"""

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for sub in ("", "orchestration"):
    p = str(ROOT / sub) if sub else str(ROOT)
    if p not in sys.path:
        sys.path.insert(0, p)
from calibration import param  # noqa: E402
from opgraph import Operation, OperationGraph, ascii_gantt, schedule  # noqa: E402

FOIL_THICKNESS = param("foil_thickness", 1.0e-5)          # m, the layer height
FOIL_BOND_SHEAR_MPA = param("foil_bond_shear_mpa", 8.0)   # MPa, lamination bond strength
ALU_DENSITY = 2710.0                                      # kg/m^3

# per-layer op durations (s); cut time is contour length / cut speed
T_FEED = 2.0            # advance + register a fresh foil layer
T_BOND = 3.0           # press / activate the bond
CUT_SPEED_MM_S = 20.0  # blade/laser contour speed

# target solids: radius(z) profiles, metres. height H, and radius as a function of z.
SOLIDS = {
    "cone":  {"H": 0.008, "r": lambda z: 0.010 * (1 - z / 0.008)},
    "dome":  {"H": 0.008, "r": lambda z: math.sqrt(max(0.0, 0.008**2 - z**2))},
    "boss":  {"H": 0.008, "r": lambda z: 0.010 if z < 0.004 else 0.006},
}


def slice_solid(shape="cone", thickness=None):
    """Slice a target solid into foil layers; quantify the stack.

    Returns per-build metrics: layer count, staircase (finite-layer) error, total
    contour cut length, stacked mass, and the delamination margin from the bond.
    """
    thickness = thickness or FOIL_THICKNESS
    H, r = SOLIDS[shape]["H"], SOLIDS[shape]["r"]
    n = max(1, int(math.ceil(H / thickness)))

    perims, areas, radii = [], [], []
    for i in range(n):
        z = (i + 0.5) * thickness
        ri = max(0.0, r(z))
        radii.append(ri)
        perims.append(2 * math.pi * ri)
        areas.append(math.pi * ri * ri)

    # staircase error: each layer is a straight-walled disc, so it misses the true
    # profile by up to |dr/dz|*t per step. RMS over the stack (metres).
    steps = [abs(radii[i] - radii[i - 1]) for i in range(1, n)]
    staircase_rms = math.sqrt(sum(s * s for s in steps) / len(steps)) if steps else 0.0

    cut_len_m = sum(perims)
    stacked_vol = sum(areas) * thickness            # m^3 of foil actually laid
    mass_g = stacked_vol * ALU_DENSITY * 1000.0

    # delamination margin: lift the part from its base, so every interface must
    # transmit the weight of the layers ABOVE it. The bond carries shear over the
    # overlap (the smaller of the two touching layers). Worst interface = the
    # margin. Shows the calibrated bond strength gating a build.
    bond_shear_pa = FOIL_BOND_SHEAR_MPA * 1e6
    areal_wt = ALU_DENSITY * 9.81 * thickness       # N per m^2 of a single layer
    suffix = [0.0] * (n + 1)                         # suffix[i] = sum(areas[i:])
    for i in range(n - 1, -1, -1):
        suffix[i] = suffix[i + 1] + areas[i]
    delam_margin = float("inf")
    for i in range(1, n):                           # interface below layer i
        weight_above = areal_wt * suffix[i]
        if weight_above <= 0:
            continue
        contact = min(areas[i - 1], areas[i])       # overlap = smaller layer
        delam_margin = min(delam_margin, bond_shear_pa * contact / weight_above)

    # build time: every layer is feed + bond + cut(contour)
    t_cut = [(2 * math.pi * ri * 1000.0) / CUT_SPEED_MM_S for ri in radii]
    build_s = sum(T_FEED + T_BOND + tc for tc in t_cut)

    return {
        "shape": shape,
        "layers": n,
        "layer_um": thickness * 1e6,
        "height_mm": H * 1000.0,
        "staircase_rms_um": staircase_rms * 1e6,
        "cut_length_m": round(cut_len_m, 2),
        "mass_g": round(mass_g, 3),
        "delam_margin": round(delam_margin, 1),
        "build_time_s": round(build_s, 1),
        "build_time_h": round(build_s / 3600.0, 2),
        "throughput_layers_per_min": round(60.0 * n / build_s, 1) if build_s else 0.0,
    }


def build_graph(shape="cone", n_sample=3) -> OperationGraph:
    """The op-graph for the first `n_sample` layers — shows the per-layer
    (feed -> bond -> cut) structure the full build repeats. One resource: the LOM
    printer is a single server, so layers are strictly sequential (unlike the
    multi-cell job, which overlaps)."""
    H, r = SOLIDS[shape]["H"], SOLIDS[shape]["r"]
    ops = []
    prev_cut = None
    for i in range(n_sample):
        ri = max(0.0, r((i + 0.5) * FOIL_THICKNESS))
        tc = (2 * math.pi * ri * 1000.0) / CUT_SPEED_MM_S
        feed, bond, cut = f"feed_{i}", f"bond_{i}", f"cut_{i}"
        needs_feed = (prev_cut,) if prev_cut else ()
        ops += [
            Operation(feed, "lom", T_FEED, needs=needs_feed),
            Operation(bond, "lom", T_BOND, needs=(feed,)),
            Operation(cut, "lom", round(tc, 2), needs=(bond,)),
        ]
        prev_cut = cut
    return OperationGraph(ops)


if __name__ == "__main__":
    m = slice_solid("cone")
    print(f"foil_lom: {m['shape']} {m['height_mm']:.0f}mm -> {m['layers']} layers "
          f"@ {m['layer_um']:.0f}um, build {m['build_time_h']}h")
    g = build_graph("cone")
    sched, mk = schedule(g)
    print(ascii_gantt(sched, mk))
