"""_shear.py — shared parameters for the self-actuated wire shear tool.

A cam-driven bypass shear, designed to the force reality (CONCEPT.md / discussion):
  * SELF-REACTING — the fixed jaw and the moving blade both live on the tool, so
    the cut force (hundreds to ~2900 N for steel wire) loops inside the tool body
    and the arm + kinematic coupling never see it.
  * BOUGHT BLADES — hardened replaceable inserts sit in pockets (build/buy: the
    cutting edge is the "buy", the housing/cam/lever are the "build").
  * CAM-DRIVEN — a NEMA17 turns a cam that closes the blade with mechanical
    advantage over a short, repeatable stroke; a return spring opens it.
  * Mounts on the tool-side kinematic coupling (parts/coupling_tool_side.py);
    motor power crosses the joint on pogo pins.

Axes: +X forward (jaws point this way), Y = motor-shaft / thickness, +Z up
(coupling on top). v1 geometry — iterate dimensions on the bench.
"""

import math

C, MN, MX = "CENTER", "MIN", "MAX"   # placeholders; parts import build123d Align

# --- coupling interface (mates to coupling_tool_side.py) ---
COUPLING_OD = 48.0
COUPLING_T = 6.0
BORE_D = 12.0           # central bore: EPM / pogo pass-through
BOLT_R = 21.0
BOLT_CLR = 3.4          # M3 clearance
MOUNT_ANGLES = (30, 150, 270)

# --- body ---
BODY_X = 36.0           # forward depth
BODY_Y = 40.0           # width / motor axis
BODY_H = 42.0           # height (fits the NEMA17 face)

# --- fixed jaw (forward tongue at the bottom) ---
JAW_X0 = 14.0           # jaw starts here (+X)
JAW_LEN = 24.0          # reaches to x = 38
JAW_Y = 9.0
JAW_Z0 = 2.0
JAW_H = 7.0             # jaw top at z = 9

# --- blade insert pocket (bought hardened blade) ---
BLADE_L = 14.0
BLADE_W = 5.0
BLADE_T = 1.6
BLADE_SCREW = 2.4       # M2 clearance
BLADE_BYPASS = 1.4      # moving blade offset in +Y to pass the fixed blade

# --- pivot for the moving blade arm ---
PIVOT_X = 16.0
PIVOT_Z = 12.0
PIVOT_D = 4.0

# --- NEMA17 motor mount (on the -Y face) ---
NEMA_PILOT_D = 22.5
NEMA_BC = 31.0          # bolt circle (holes at ±15.5)
NEMA_HOLE = 3.2         # M3
NEMA_SHAFT_CLR = 11.0
MOTOR_Z = 21.0          # centre height of the motor on the -Y face

# --- cam ---
CAM_D = 18.0
CAM_T = 6.0
CAM_ECC = 3.0           # eccentricity -> blade stroke
SHAFT_D = 5.0           # NEMA17 D-shaft
SHAFT_FLAT = 0.5        # flat depth on the D

# --- wire guide ---
WIRE_D = 2.2            # 1.6 mm wire + clearance


def pos(r, angle_deg):
    return r * math.cos(math.radians(angle_deg)), r * math.sin(math.radians(angle_deg))
