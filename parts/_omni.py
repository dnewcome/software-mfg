"""_omni.py — shared parametric geometry for the reverse-engineered omni wheel.

Grey-box reverse engineering (not tracing): the STRUCTURE is known — an omni wheel is barrel
rollers on tangent axes, each roller's outer surface lying on the wheel's pitch circle
(radius R_EFF) so the barrels blend into a round OD. MEASURE your wheel and set R_EFF /
N_ROLLERS / MOUNT_R; the rest derives. Key identities:

    rho(z) = R_EFF - hypot(MOUNT_R, z)      # barrel radius keeps the surface on the OD circle
    HALF_L = MOUNT_R * tan(pi/N) - gap/2    # roller half-length (with a gap for the hub)

**Continuity fix:** a single row of rollers with gaps drops into a gap each turn — it bumps,
it doesn't roll. So the wheel is TWO staggered rows (a "double omni wheel"): row 2 is rotated
half a pitch, so its rollers sit over row 1's gaps. Contact is continuous iff each roller's
angular coverage half-angle >= 90/N degrees (see continuity()).
"""
import math

# FITTED to the XRP "Omni-Directional Kiwi Bot" wheel (omni-wheel-shell.step + omni-roller.stl).
# Design closes on clean integers: a Ø70 wheel arc (R_EFF 35) with Ø20 barrel rollers (barrel_max
# 10), so MOUNT_R = R_EFF - 10 = 25 (matches the measured pin pitch); rollers 30 mm long (HALF_L
# 15); 4/row × 2 staggered rows. Coverage atan(15/25)=31deg > need 90/4=22.5deg -> continuous.
# (Replaces the earlier OD60/10-roller photo wheel; see software-mfg/WHEELS.md.)
R_EFF = 35.0        # wheel effective radius (mm) -> 70 mm OD.        MEASURE (Ø70 wheel arc)
N_ROLLERS = 4       # rollers PER ROW — count them on the real wheel. MEASURE (2×4 = 8)
MOUNT_R = 25.0      # roller-axis distance from wheel centre (pitch). = R_EFF - barrel_max (Ø20 roller)
PIN_D = 3.0         # axle pin (3 mm dowel / M3); roller bore Ø3.15
ROLLER_BORE = 3.4   # roller spins on the pin -> bore > pin
HUB_PIN_BORE = 3.2  # round seat the pin snaps INTO (holds the pin; the roller spins on it)
PIN_SNAP_MOUTH = 2.4  # radial entry throat, NARROWER than the pin -> lips flex, pin snaps past &
#                       is retained. ~0.5mm snap interference (throat < PIN_D); inboard seat = the nest.
ROLLER_SAMPLES = 28
ROLLER_GAP_MM = 10.0  # tangential gap between rollers in a row -> room for the hub + spin clearance
# MEASURED roller half-length: the XRP roller is 30 mm long (omni-roller.stl) -> HALF_L 15. Set to
# a number to use the measured length; None derives it from FULL_HALF_L - ROLLER_GAP_MM/2 (the
# "rollers meet at the pitch angle" identity). Measure it directly — barrels overhang the pin span.
ROLLER_HALF_L = 15.0
ROWS = 2              # two axially-offset, half-pitch-staggered rows -> continuous contact
# axial half-separation of the two rows. None -> BARREL_MAX + 1 (rows just clear). Set it SMALLER
# to nest the rows (the real XRP wheel's rows are 19 mm apart -> 9.5), narrowing the wheel — the
# 45deg stagger keeps the interleaved barrels from colliding (verified by the interference gate).
ROW_SEP_HALF = 9.5

# drive interface to the STS3215 horn — from the ST-3215-C047 datasheet (§11 accessories horn):
# horn OD Ø19.95, hub Ø9, bolt circle Ø14, 4× Ø3.2 (M3), 25T/Ø5.9 spline, M3×6 retaining screw.
HUB_BORE = 9.2       # clears the horn's Ø9 hub boss
HORN_BC_D = 14.0     # datasheet Ø14 bolt circle
HORN_N = 4           # datasheet 4-M3
HORN_SCREW = 3.4     # M3 clearance (horn holes are Ø3.2; wheel bolts through)
HORN_RECESS_D = 20.5      # pocket that seats the Ø19.95 horn disc (on the servo-side boss end)
HORN_RECESS_DEPTH = 3.0
MOUNT_BOSS_D = 22.0       # servo-side standoff boss -> rollers clear the STS3215 body; hosts the horn
MOUNT_BOSS_H = 8.0
BACK_ACCESS_D = 18.0      # back-face counterbore so the M3 screws only span the boss (short screws)

FULL_HALF_L = MOUNT_R * math.tan(math.pi / N_ROLLERS)     # where rollers would just meet
# derived length (rollers nearly meet, minus a hub gap) unless a measured length overrides it
HALF_L = ROLLER_HALF_L if ROLLER_HALF_L is not None else FULL_HALF_L - ROLLER_GAP_MM / 2
BARREL_MAX = R_EFF - MOUNT_R                              # barrel radius at its centre
END_R = R_EFF - math.hypot(MOUNT_R, HALF_L)              # barrel radius at the (shortened) ends
ROW_STAGGER = 180.0 / N_ROLLERS                          # deg: row-2 rotated half a pitch
ROW_Z = ROW_SEP_HALF if ROW_SEP_HALF is not None else BARREL_MAX + 1.0   # axial half-separation


def rho(z):
    """Barrel radius at axial station z, holding the outer surface on the wheel pitch circle."""
    return R_EFF - math.hypot(MOUNT_R, z)


def roller_center(i, row=0):
    """((x, y, z), angle_deg) of roller i in `row`. Row 1 is staggered half a pitch and offset
    axially so its rollers cover row 0's gaps."""
    a = 2 * math.pi * i / N_ROLLERS + (math.radians(ROW_STAGGER) if row else 0.0)
    z = ROW_Z if row else -ROW_Z
    return (MOUNT_R * math.cos(a), MOUNT_R * math.sin(a), z), math.degrees(a)


def coverage_half_deg():
    """Half the azimuth a single roller keeps at the OD, ESTIMATED from the axle-pin span
    (surface on R_EFF out to ±HALF_L). This is a LOWER BOUND: barrels that overhang their pins
    cover more (the kiwi-v10 wheel covers ~±28deg vs ~±11 from its pin span). The authoritative
    continuity test measures the ASSEMBLED geometry — scripts/omni_check.py:geometric_continuity."""
    return math.degrees(math.atan(HALF_L / MOUNT_R))


def continuity():
    """ANALYTIC ESTIMATE (advisory): two staggered rows -> combined rollers every 180/N deg, each
    covering ±coverage; contact is continuous iff coverage >= 90/N (adjacent arcs meet). Because
    coverage_half_deg() is a lower bound, this can FALSE-NEGATIVE for barrels that overhang the
    pins — the gate uses the geometric OD-coverage measurement, not this."""
    need = 90.0 / N_ROLLERS
    cov = coverage_half_deg()
    return {"coverage_deg": round(cov, 1), "need_deg": round(need, 1),
            "continuous": cov >= need, "margin": round(cov / need, 2)}


def validity():
    w = []
    if R_EFF <= MOUNT_R:
        w.append("R_EFF must exceed MOUNT_R")
    if END_R <= ROLLER_BORE / 2 + 1.0:
        w.append("barrel ends too thin for the bore (raise R_EFF or MOUNT_R)")
    if BARREL_MAX <= 2:
        w.append("barrel too shallow (rollers won't contact ground)")
    # NB: contact continuity is validated GEOMETRICALLY on the assembled wheel
    # (scripts/omni_check.py:geometric_continuity), not by the analytic continuity() lower bound.
    return w
