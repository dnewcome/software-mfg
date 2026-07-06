"""foil_former.py — a CNC foil bender: fold flat foil stock into stiff profiles.

The analog of the wire bender, lifted one dimension. The wire bender walks a
(feed, rotate, bend) program into a 3D space curve; the foil former walks a
(feed, bend) program into a folded 2D cross-section — a channel, a corrugation —
which a feed axis then extrudes into a 3D stiffened panel. Foil has essentially no
bending stiffness of its own (~t^3), so ALL stiffness is geometric: ribs and folds.

Like the wire bender, the physics that matters is SPRINGBACK, plus foil's fast
WORK-HARDENING: each re-bend (reversal) of a crease needs more moment, springs
back more, and eventually cracks. Both are CALIBRATED parameters
(calibration/store.json), not first-principles constants — a new roll of foil is a
new operating point. No physical former exists yet, so these parameters are
UNANCHORED: the staleness stamp marks every result here as a PREDICTION until a
real machine is built and measured.

Forming strategy: to land a crease at a target angle, the tool must OVERBEND so the
elastic springback relaxes it to target — exactly the overbend the wire bender uses.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from calibration import param  # noqa: E402

# --- calibrated foil behaviour (unanchored estimates until a former is built) ---
FOIL_THICKNESS = param("foil_thickness", 1.0e-5)          # m
FOIL_SPRINGBACK_DEG = param("foil_springback_deg", 4.0)   # deg, at a 90 deg reference bend
FOIL_WORKHARDEN_GAIN = param("foil_workharden_gain", 0.35)  # extra springback per prior reversal
FOIL_CRACK_BENDS = int(param("foil_crack_bends", 4))      # reversals of ONE crease before it cracks

# cycle-time model (mirrors the wire bender's axis-speed model)
FEED_MM_S = 400.0 / 60.0
BEND_DEG_S = 90.0
OP_OVERHEAD_S = 0.12

# A forming program: list of (op, value). feed mm along the strip; bend deg at a
# crease (+/- = mountain/valley). These make stiff open sections from flat foil.
PROGRAMS = {
    # U-channel: two right-angle folds -> a stiff open section
    "channel": [("feed", 10.0), ("bend", 90.0), ("feed", 20.0), ("bend", 90.0), ("feed", 10.0)],
    # trapezoidal corrugation: alternating folds -> a panel stiffener (each crease fresh)
    "corrugation": [("feed", 6.0), ("bend", 115.0), ("feed", 6.0), ("bend", -115.0),
                    ("feed", 6.0), ("bend", 115.0), ("feed", 6.0), ("bend", -115.0),
                    ("feed", 6.0)],
}


def springback_deg(theta_target, reversals=0):
    """Elastic recovery angle after forming a crease to `theta_target` (deg).
    Scales with bend angle; grows with work-hardening from prior reversals."""
    base = FOIL_SPRINGBACK_DEG * (abs(theta_target) / 90.0)
    return base * (1.0 + FOIL_WORKHARDEN_GAIN * reversals)


def overbend_deg(theta_target, reversals=0):
    """Commanded bend so the crease RELAXES to theta_target after springback.
    (Springback is proportional to the commanded angle, so this is closed-form.)"""
    k = FOIL_SPRINGBACK_DEG * (1.0 + FOIL_WORKHARDEN_GAIN * reversals) / 90.0
    return theta_target / (1.0 - k) if k < 1.0 else float("inf")


def crease_reuse_ok(reversals) -> bool:
    """A crease can be reversed only so many times before it cracks (fatigue)."""
    return reversals < FOIL_CRACK_BENDS


def bend_duration(program) -> float:
    """Cycle time (s) for a forming program from the axis-speed model."""
    t = 0.0
    for op, v in program:
        t += (abs(v) / FEED_MM_S) if op == "feed" else (abs(overbend_deg(v)) / BEND_DEG_S)
        t += OP_OVERHEAD_S
    return round(t, 2)


def simulate(program_name="channel"):
    """Walk a forming program into the folded 2D profile it produces.

    The polyline uses the TARGET angles (achieved shape, since we overbend to hit
    them); `bends` reports the tool command + springback + feasibility per crease.
    Parallels wirebender_cell.simulate — the foil former's real forward model.
    """
    import numpy as np
    prog = PROGRAMS[program_name]
    pos = np.array([0.0, 0.0])
    heading = 0.0
    pts = [pos.copy()]
    bends = []
    feed_total = 0.0
    for op, v in prog:
        if op == "feed":
            hr = np.radians(heading)
            pos = pos + v * np.array([np.cos(hr), np.sin(hr)])
            pts.append(pos.copy())
            feed_total += v
        elif op == "bend":
            heading += v                       # achieved == target (overbent to here)
            cmd = overbend_deg(v)
            bends.append({
                "target": v,
                "command": round(cmd, 1),
                "springback": round(springback_deg(v), 2),
                "feasible": abs(cmd) < 175.0,  # can't fold past ~flat-on-itself
            })
    return {
        "points": [p.tolist() for p in pts],
        "profile_length": round(feed_total, 2),      # mm of stock consumed (flat)
        "n_bends": len(bends),
        "bends": bends,
        "max_command": round(max((abs(b["command"]) for b in bends), default=0.0), 1),
        "duration": bend_duration(prog),
        "program": program_name,
    }


if __name__ == "__main__":
    r = simulate("channel")
    print(f"foil_former: {r['program']} — {r['n_bends']} folds, "
          f"{r['profile_length']} mm stock, overbend to {r['max_command']} deg, {r['duration']}s")
