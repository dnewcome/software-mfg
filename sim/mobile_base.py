"""mobile_base.py — the material-handling platform: a mobile base that carries an arm.

Physics-first (analytical model -> validity checks -> then CAD/BOM). The base drives up
to a station (a 3D printer, a fixture), **locks**, and the arm reaches out. The design
question is not "can it drive" — small steppers do that — it is:

  **How much static force/torque can the base resist WHEN LOCKED, before it moves?**

An arm reaching out is a reaction force `F` at the tool at height `z`, i.e. a force + a
tip-over moment on the base. Three ways the "locked" base gives — the real limit is the
WORST (minimum) of them:

  1. BACK-DRIVE  the wheels roll: resisted by motor holding torque / wheel radius.
                 Steppers give a SOFT hold (slip poles under overload); a worm gearbox or
                 a brake or deployable feet give a HARD hold. This is a design lever.
  2. SLIDE       the whole base skids: friction-limited, mu * m * g. Locking wheels does
                 nothing beyond this.
  3. TIP-OVER    the base rotates about its front support edge: resisted by footprint +
                 CG, NOT by the motors at all. Usually the binding limit for a tall arm on
                 a small base — and the one a "lock the wheels" instinct misses.

`max_hold_force()` returns the min of the three (the honest limit) and which one binds.
Uncertain params (floor friction, stepper holding derate, gear efficiency) are CALIBRATED
and seeded UNANCHORED — every number here is a PREDICTION until a bench pull-test on a
real base anchors them (the point of "make one soon to verify"). Reach direction = +x.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from calibration import param  # noqa: E402

G = 9.81

# Calibrated, uncertain, UNANCHORED -> results read as PREDICTION until a real base is measured.
MU_SLIDE = param("base_mu_slide", 0.65)          # tire/floor static friction (PU on sealed concrete)
MU_ROLLER = param("base_roller_mu", 0.05)        # transverse resistance of a FREE mecanum/omni roller
STEPPER_HOLD_DERATE = param("stepper_hold_derate", 0.7)  # usable static hold vs rated holding torque
GEAR_EFF = param("base_gear_eff", 0.9)           # gearbox efficiency (planetary)
ROLL_RESIST = param("base_roll_coeff", 0.03)     # rolling resistance coefficient


@dataclass
class Motor:
    name: str
    holding_nm: float        # rated holding torque at the motor shaft (energized)
    rated_nm: float          # continuous torque available for drive
    max_rpm: float           # usable speed before torque collapses
    mass_kg: float = 0.28


# A small catalogue of real, buyable motors (typical catalogue values; verify per vendor).
NEMA17 = Motor("NEMA17-59Ncm", holding_nm=0.59, rated_nm=0.40, max_rpm=400, mass_kg=0.28)
NEMA23 = Motor("NEMA23-19kg", holding_nm=1.26, rated_nm=0.90, max_rpm=500, mass_kg=0.60)
NEMA23_HT = Motor("NEMA23-30kg", holding_nm=3.0, rated_nm=2.0, max_rpm=450, mass_kg=1.10)


@dataclass
class BaseDesign:
    name: str
    layout: str                  # "diff2" | "mecanum4" | "footed4"
    mass_base_kg: float          # chassis + battery + electronics + motors + riser
    motor: Motor
    n_drive: int
    gear_ratio: float            # motor:wheel reduction (>1 multiplies wheel torque)
    wheel_radius_m: float
    # support polygon (ground contacts) in the reach frame, metres from base centre:
    x_front: float               # forward-most support edge (+x, toward the work)
    x_rear: float                # rear-most support edge (-x)
    half_track: float            # lateral half-width of support (y)
    cg_height_m: float           # base CG height
    backdrivable: bool = True    # False for worm gearbox / brake / feet -> hard lock
    roller: str = "solid"        # transverse behaviour: solid | passive | active | locked
    note: str = ""

    def wheel_holding_nm(self):
        """Static holding torque delivered at ONE wheel (energized stepper, derated)."""
        return self.motor.holding_nm * STEPPER_HOLD_DERATE * self.gear_ratio * GEAR_EFF


@dataclass
class ArmLoad:
    """The arm + payload the base carries, at a reach pose (worst case = fully extended)."""
    mass_arm_kg: float
    arm_mount_x: float           # where the arm base sits on the deck (+x forward of centre)
    arm_mount_height: float      # deck-top to arm base (a riser lifts it to reach a printer)
    arm_cg_dx: float             # horizontal offset of the arm CG when extended (+x)
    arm_cg_dz: float             # arm CG height above its mount
    payload_kg: float
    ee_reach_x: float            # tool horizontal offset from base centre (+x)
    ee_height: float             # tool height above the ground

    def bodies(self):
        """(mass, x, z) for each mass: arm and payload (base added by the design)."""
        return [
            (self.mass_arm_kg, self.arm_mount_x + self.arm_cg_dx, self.arm_mount_height + self.arm_cg_dz),
            (self.payload_kg, self.ee_reach_x, self.ee_height),
        ]


def combined_cg(design: BaseDesign, load: ArmLoad):
    """Total mass and its (x, z) centre of gravity."""
    masses = [(design.mass_base_kg, 0.0, design.cg_height_m)] + load.bodies()
    m = sum(w for w, _, _ in masses)
    x = sum(w * xi for w, xi, _ in masses) / m
    z = sum(w * zi for w, _, zi in masses) / m
    return m, x, z


def slide_limit_N(design, load):
    m, _, _ = combined_cg(design, load)
    return MU_SLIDE * m * G


def backdrive_limit_N(design, load):
    """Horizontal force before the driven wheels roll. Hard-lock designs (worm/brake/feet)
    are limited only by friction (return slide limit as a proxy for 'won't back-drive')."""
    if not design.backdrivable:
        return slide_limit_N(design, load)          # no back-drive path; slide/tip bind instead
    tractive = design.n_drive * design.wheel_holding_nm() / design.wheel_radius_m
    return min(tractive, slide_limit_N(design, load))   # can't exceed available friction


def lateral_hold_N(design, load):
    """Max SIDEWAYS force the locked base resists — the axis wheel choice decides, and the
    one passive mecanum quietly fails. `solid` wheels can't roll sideways (full friction);
    `passive` mecanum/omni rollers free-spin (≈zero motor hold, only roller-bearing drag);
    `active` (differentially-driven) rollers hold via a motor like the drive axis; `locked`
    feet are rigid (friction)."""
    m, _, _ = combined_cg(design, load)
    if design.roller == "passive":
        return MU_ROLLER * m * G                      # rollers just roll -> almost no hold
    if design.roller == "active":
        tractive = design.n_drive * design.wheel_holding_nm() / design.wheel_radius_m
        return min(tractive, MU_SLIDE * m * G)        # geared rollers held by a motor
    return MU_SLIDE * m * G                            # solid / locked: full friction


def tip_force_N(design, load):
    """Max horizontal tool force (+x) before the base tips about its front support edge.
    Moment balance about (x_front, z=0): F_push * z_ee = m * g * (x_front - x_cg)."""
    m, x_cg, _ = combined_cg(design, load)
    restoring = m * G * (design.x_front - x_cg)     # >0 stable; negative already tipping
    if load.ee_height <= 1e-6:
        return float("inf")
    return restoring / load.ee_height


def static_margin_m(design, load):
    """How far the CG sits inside the front support edge (m). <=0 means it tips just
    standing there (before any push)."""
    _, x_cg, _ = combined_cg(design, load)
    return design.x_front - x_cg


def max_hold_force(design, load):
    """The headline: max static tool force the LOCKED base resists, and what binds."""
    limits = {"tip": tip_force_N(design, load),
              "slide": slide_limit_N(design, load),
              "backdrive": backdrive_limit_N(design, load)}
    binding = min(limits, key=limits.get)
    return {"limit_N": round(limits[binding], 1), "binding": binding,
            "modes_N": {k: round(v, 1) for k, v in limits.items()},
            "static_margin_mm": round(static_margin_m(design, load) * 1000, 1)}


def motor_for_hold(design, load, target_force_N):
    """Required motor holding torque so back-drive isn't the limit for target_force_N."""
    wheel_nm = target_force_N * design.wheel_radius_m / design.n_drive
    motor_nm = wheel_nm / (design.gear_ratio * GEAR_EFF * STEPPER_HOLD_DERATE)
    return {"wheel_holding_nm": round(wheel_nm, 2), "motor_holding_nm": round(motor_nm, 2)}


def drive_check(design, load, accel=0.4, ramp_deg=3.0, top_speed=0.4):
    """Can the motors drive the loaded base: accelerate, climb a small ramp/threshold, at
    speed? Reaction/holding aside, this is the 'can it move the load' question."""
    import math
    m, _, _ = combined_cg(design, load)
    f_drive = m * (accel + G * math.sin(math.radians(ramp_deg))) + ROLL_RESIST * m * G
    wheel_nm = f_drive * design.wheel_radius_m / design.n_drive
    motor_nm = wheel_nm / (design.gear_ratio * GEAR_EFF)
    rpm = (top_speed / design.wheel_radius_m) * design.gear_ratio * 60 / (2 * math.pi)
    return {"drive_force_N": round(f_drive, 1), "motor_torque_nm": round(motor_nm, 2),
            "have_nm": round(design.motor.rated_nm, 2), "torque_ok": motor_nm <= design.motor.rated_nm,
            "top_rpm": round(rpm), "speed_ok": rpm <= design.motor.max_rpm,
            "total_mass_kg": round(m, 2)}


def validity(design, load):
    """Physics-first sanity flags — surface the honest caveats, don't hide them."""
    warn = []
    m, x_cg, z_cg = combined_cg(design, load)
    if static_margin_m(design, load) <= 0:
        warn.append("CG is OUTSIDE the front support edge — tips while just standing")
    if design.backdrivable and backdrive_limit_N(design, load) < slide_limit_N(design, load):
        warn.append("motors back-drive BEFORE the base slides — gearing/hold too weak; "
                    "add reduction, a brake, or deployable feet")
    if z_cg > design.half_track:
        warn.append(f"CG height {z_cg*1000:.0f}mm exceeds half-track {design.half_track*1000:.0f}mm "
                    "— lateral tip risk during a turn")
    if not (0.2 <= MU_SLIDE <= 1.0):
        warn.append(f"friction mu={MU_SLIDE} out of plausible range")
    if lateral_hold_N(design, load) < 0.5 * max_hold_force(design, load)["limit_N"]:
        warn.append(f"lateral hold {lateral_hold_N(design, load):.0f}N << forward hold — a "
                    "sideways arm push or yaw torque skids it; passive rollers don't lock")
    return warn


def evaluate(design, load, target_force_N=15.0):
    hold = max_hold_force(design, load)
    lat = lateral_hold_N(design, load)
    return {"design": design.name, "layout": design.layout,
            "hold": hold, "lateral_hold_N": round(lat, 1),
            "sized_for_target": motor_for_hold(design, load, target_force_N),
            "drive": drive_check(design, load), "warnings": validity(design, load),
            "pass": hold["limit_N"] >= target_force_N and hold["static_margin_mm"] > 0
                    and lat >= target_force_N}


# ---- reference designs + the near-term scenario -------------------------------------------------

# SO-101 reaching into a floor-standing Bambu P1S to extract a printed part. The arm is light
# but sits on a ~0.30 m riser to reach the build plate, which lifts the CG (the hard part).
PRINTER_PICK = ArmLoad(
    mass_arm_kg=1.5, arm_mount_x=0.05, arm_mount_height=0.30,
    arm_cg_dx=0.12, arm_cg_dz=0.10, payload_kg=0.25, ee_reach_x=0.32, ee_height=0.30)

DESIGNS = {
    # A — the simplest: 2 driven wheels + a front caster. Smallest, cheapest; the caster
    #     gives the forward support the arm needs. Direct-drive steppers are too soft, so
    #     spec a 5:1 planetary so slide/tip bind, not the motors.
    "diff2": BaseDesign("diff2 (2wd + caster)", "diff2", mass_base_kg=5.0, motor=NEMA17,
                        n_drive=2, gear_ratio=5.0, wheel_radius_m=0.05,
                        x_front=0.18, x_rear=-0.12, half_track=0.15, cg_height_m=0.12,
                        roller="solid", note="caster forward for reach; riser raises arm CG"),
    # B — 4 PASSIVE mecanum: holonomic to drive, but the transverse rollers free-spin, so a
    #     locked base barely resists a sideways push — the trap for an arm platform.
    "mecanum4": BaseDesign("mecanum4 (passive)", "mecanum4", mass_base_kg=8.0, motor=NEMA17,
                           n_drive=4, gear_ratio=5.0, wheel_radius_m=0.05,
                           x_front=0.16, x_rear=-0.16, half_track=0.16, cg_height_m=0.12,
                           roller="passive", note="holonomic but ≈no lateral hold when locked"),
    # C — differentially-driven ACTIVE omni (the wheel in the video): geared rollers held by a
    #     motor -> holonomic AND resists lateral load. Complex/backlash, but locks both axes.
    "omni_diff": BaseDesign("omni_diff (active rollers)", "omni_diff", mass_base_kg=9.0,
                            motor=NEMA17, n_drive=4, gear_ratio=5.0, wheel_radius_m=0.06,
                            x_front=0.18, x_rear=-0.18, half_track=0.18, cg_height_m=0.12,
                            roller="active", note="driven rollers hold laterally; gear backlash"),
    # D — the robust one: 4wd for travel + DEPLOYABLE FEET that lift the base off the wheels
    #     and lock it rigid (non-backdrivable, wide stance). Drive on wheels, work on feet.
    "footed4": BaseDesign("footed4 (feet lock)", "footed4", mass_base_kg=9.0, motor=NEMA17,
                          n_drive=4, gear_ratio=5.0, wheel_radius_m=0.05,
                          x_front=0.22, x_rear=-0.22, half_track=0.22, cg_height_m=0.12,
                          backdrivable=False, roller="locked", note="feet at 0.44m span, rigid lock"),
}


if __name__ == "__main__":
    print(f"scenario: SO-101 extracting a {PRINTER_PICK.payload_kg}kg part at "
          f"{PRINTER_PICK.ee_reach_x*100:.0f}cm reach, {PRINTER_PICK.ee_height*100:.0f}cm high\n")
    for key, d in DESIGNS.items():
        r = evaluate(d, PRINTER_PICK, target_force_N=15.0)
        h = r["hold"]
        print(f"[{d.name}]  mass {combined_cg(d, PRINTER_PICK)[0]:.1f}kg  "
              f"footprint {(d.x_front-d.x_rear)*100:.0f}x{d.half_track*200:.0f}cm")
        print(f"   FWD HOLD {h['limit_N']}N (binds: {h['binding']}; "
              f"tip {h['modes_N']['tip']} / slide {h['modes_N']['slide']} / "
              f"backdrive {h['modes_N']['backdrive']} N)  |  LAT HOLD {r['lateral_hold_N']}N  "
              f"margin {h['static_margin_mm']}mm")
        print(f"   drive: {r['drive']['motor_torque_nm']}Nm needed vs {r['drive']['have_nm']}Nm "
              f"({'ok' if r['drive']['torque_ok'] else 'UNDERPOWERED'}), "
              f"{r['drive']['top_rpm']}rpm ({'ok' if r['drive']['speed_ok'] else 'TOO FAST'})")
        for w in r["warnings"]:
            print(f"   ! {w}")
        print(f"   => {'PASS' if r['pass'] else 'FAIL'} (>=15N hold, CG inside footprint) "
              f"[PREDICTION until a bench pull-test anchors mu/hold]\n")
