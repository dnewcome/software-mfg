"""_omni.py — shared parametric geometry for the reverse-engineered omni wheel.

Grey-box reverse engineering (not tracing): the STRUCTURE is known — an omni wheel is N
barrel rollers on tangent axes, each roller's outer surface lying on the wheel's pitch
circle (radius R_EFF) so the barrels blend into a continuous round OD. MEASURE your physical
wheel and set R_EFF / N_ROLLERS / MOUNT_R / bores; every other dimension derives from the
constraint. The key identity:

    rho(z) = R_EFF - hypot(MOUNT_R, z)      # barrel radius keeps the surface on the OD circle
    HALF_L = MOUNT_R * tan(pi / N_ROLLERS)  # half roller length so adjacent rollers just meet
"""
import math

R_EFF = 30.0        # wheel effective radius (mm) -> 60 mm OD.        MEASURE
N_ROLLERS = 5       # roller count — count them on the real wheel.    MEASURE
MOUNT_R = 21.0      # roller-axis distance from wheel centre (pitch). MEASURE
#                     (21 with N=5 -> 18mm barrels that don't self-overlap; verified by interference)
PIN_D = 3.0         # axle pin (3 mm dowel / M3)
ROLLER_BORE = 3.4   # roller spins on the pin -> bore > pin
ROLLER_SAMPLES = 28
ROLLER_GAP_MM = 10.0  # tangential gap between adjacent rollers -> room for the hub + spin clearance

# drive interface to the STS3215 horn (same approach as parts/base_wheel.py) — MEASURE horn
HUB_BORE = 8.5
HORN_BC_D = 16.0
HORN_N = 4
HORN_SCREW = 2.7

FULL_HALF_L = MOUNT_R * math.tan(math.pi / N_ROLLERS)     # where rollers would just meet
HALF_L = FULL_HALF_L - ROLLER_GAP_MM / 2                  # shortened -> a gap for the arm
BARREL_MAX = R_EFF - MOUNT_R                              # barrel radius at its centre
END_R = R_EFF - math.hypot(MOUNT_R, HALF_L)              # barrel radius at the (shortened) ends


def rho(z):
    """Barrel radius at axial station z, holding the outer surface on the wheel pitch circle."""
    return R_EFF - math.hypot(MOUNT_R, z)


def roller_center(i):
    """(x, y) of roller i's centre in the wheel plane, and its tangent-axis unit vector."""
    a = 2 * math.pi * i / N_ROLLERS
    c = (MOUNT_R * math.cos(a), MOUNT_R * math.sin(a))
    tangent = (-math.sin(a), math.cos(a))
    return c, tangent, math.degrees(a)


def validity():
    w = []
    if R_EFF <= MOUNT_R:
        w.append("R_EFF must exceed MOUNT_R")
    if END_R <= ROLLER_BORE / 2 + 1.0:
        w.append("barrel ends too thin for the bore (raise R_EFF or MOUNT_R)")
    if BARREL_MAX <= 2:
        w.append("barrel too shallow (rollers won't contact ground)")
    return w
