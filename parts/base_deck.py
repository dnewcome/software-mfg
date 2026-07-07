"""base_deck.py — mobile-base chassis deck plate (the diff2 v0).   py cad -> build/base_deck.stl

A flat deck the arm riser, motors, caster, and battery bolt to. Sized to the diff2 design
in sim/mobile_base.py (300x240 footprint, front caster for reach). Wheel cutouts let 100mm
wheels rise past the deck to keep it low (a low deck = low CG = the tip-over margin that
matters). Mounting patterns: 4 corner holes (frame/standoffs), a central SO-101 arm-riser
pattern, two side motor-bracket patterns, a front caster pattern. Keep the deck LOW and the
riser only as tall as the printer plate needs — CG height is the binding constraint.
"""
import os

from build123d import *

DECK_L = 300.0     # x, reach direction (front caster gives forward support)
DECK_W = 240.0     # y, track
DECK_T = 6.0       # plate thickness

M5_CLR = 5.5       # corner / frame bolts
M4_CLR = 4.5       # motor bracket / caster bolts
M3_CLR = 3.4       # arm riser bolts

CORNER_INSET = 14.0
ARM_PATTERN = 45.0     # SO-101 riser: 4x M3 on a 45mm square, deck centre
CASTER_PATTERN = 32.0  # front caster: 4x M4 on a 32mm square
CASTER_X = 120.0       # caster forward of centre (matches x_front support)
WHEEL_CUT_L = 104.0    # slot for a 100mm wheel to rise through
WHEEL_CUT_W = 26.0
WHEEL_X = -20.0        # drive axle a little behind centre
MOTOR_BOLT = 31.0      # NEMA17 face bolt square


def _holes(d, locs, depth=DECK_T + 2):
    cut = None
    for (x, y) in locs:
        c = Pos(x, y, -1) * Cylinder(d / 2, depth, align=(Align.CENTER, Align.CENTER, Align.MIN))
        cut = c if cut is None else cut + c
    return cut


def _build():
    p = Box(DECK_L, DECK_W, DECK_T, align=(Align.CENTER, Align.CENTER, Align.MIN))

    holes = []
    # 4 corner frame holes
    cx, cy = DECK_L / 2 - CORNER_INSET, DECK_W / 2 - CORNER_INSET
    holes += [(sx * cx, sy * cy) for sx in (-1, 1) for sy in (-1, 1) for (d,) in [(M5_CLR,)]]
    corner = _holes(M5_CLR, [(sx * cx, sy * cy) for sx in (-1, 1) for sy in (-1, 1)])
    # central arm-riser pattern (M3)
    a = ARM_PATTERN / 2
    arm = _holes(M3_CLR, [(sx * a, sy * a) for sx in (-1, 1) for sy in (-1, 1)])
    # front caster pattern (M4)
    cp = CASTER_PATTERN / 2
    caster = _holes(M4_CLR, [(CASTER_X + sx * cp, sy * cp) for sx in (-1, 1) for sy in (-1, 1)])
    # two side motor-bracket patterns (M4), inboard of each wheel cut
    mb = MOTOR_BOLT / 2
    motor = None
    for side in (-1, 1):
        yb = side * (DECK_W / 2 - 30.0)
        m = _holes(M4_CLR, [(WHEEL_X + sx * mb, yb + sy * mb) for sx in (-1, 1) for sy in (-1, 1)])
        motor = m if motor is None else motor + m

    p -= corner + arm + caster + motor

    # wheel cutouts on each side edge (through slots)
    for side in (-1, 1):
        yc = side * (DECK_W / 2 - WHEEL_CUT_W / 2 + 1.0)
        p -= Pos(WHEEL_X, yc, -1) * Box(WHEEL_CUT_L, WHEEL_CUT_W, DECK_T + 2,
                                        align=(Align.CENTER, Align.CENTER, Align.MIN))
    return p


part = _build()   # module-level built solid (repo convention: check_parts reads `part`)


if __name__ == "__main__":
    os.makedirs("build", exist_ok=True)
    export_stl(part, "build/base_deck.stl")
    import trimesh
    m = trimesh.load("build/base_deck.stl")
    print("base_deck:", (m.bounds[1] - m.bounds[0]).round(1),
          "bodies:", len(m.split(only_watertight=False)), "watertight:", m.is_watertight)
