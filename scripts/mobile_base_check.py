#!/usr/bin/env python3
"""Gate: the mobile-base model is physically self-consistent + the near-term build is viable.

The near-term milestone: an SO-101-class arm on a mobile base drives to a floor-standing
3D printer, locks, and extracts a printed part. This gate asserts the physics:
  - tip-over (footprint + CG), NOT motor lock, is the binding forward limit — the headline;
  - PASSIVE mecanum fails the lateral-hold test (free-spinning rollers don't lock) — the
    teaching control that justifies solid / active-omni / footed wheels for an arm platform;
  - the gearing is chosen so the motors don't back-drive before the base slides/tips;
  - light-arm drive torque + speed sit inside a NEMA-17-class motor;
  - at least one buildable design clears the scenario with margin.
Numbers are PREDICTIONS until a bench pull-test anchors mu / holding torque.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sim"))
import mobile_base as mb  # noqa: E402

TARGET_N = 15.0   # a stuck-part pull the locked base must resist at the tool


def main() -> int:
    problems = []
    load = mb.PRINTER_PICK
    results = {k: mb.evaluate(d, load, TARGET_N) for k, d in mb.DESIGNS.items()}

    # 1. tip-over binds forward on every design — the point (motors can't fix a footprint)
    for k, r in results.items():
        if r["hold"]["binding"] != "tip":
            problems.append(f"{k}: expected tip-over to bind forward, got {r['hold']['binding']}")

    # 2. passive mecanum must FAIL on lateral hold; solid/active/footed must PASS overall
    if results["mecanum4"]["pass"]:
        problems.append("passive mecanum wrongly passed — its rollers can't hold laterally")
    if results["mecanum4"]["lateral_hold_N"] > TARGET_N:
        problems.append(f"passive mecanum lateral hold {results['mecanum4']['lateral_hold_N']}N "
                        "should be far below target (free rollers)")
    for k in ("diff2", "omni_diff", "footed4"):
        if not results[k]["pass"]:
            problems.append(f"{k} should clear the printer-pick scenario: {results[k]['hold']}")

    # 3. active-omni recovers lateral hold vs passive (the wheel-choice lesson, quantified)
    if results["omni_diff"]["lateral_hold_N"] <= 5 * results["mecanum4"]["lateral_hold_N"]:
        problems.append("active omni rollers should hold far more laterally than passive")

    # 4. no design back-drives before it slides (gearing sized right)
    for k, r in results.items():
        m = r["hold"]["modes_N"]
        if m["backdrive"] < m["slide"] - 0.1:
            problems.append(f"{k}: motors back-drive ({m['backdrive']}N) before sliding "
                            f"({m['slide']}N) — under-geared")

    # 5. drive torque + speed fit a NEMA-17-class motor (the arm is light; holding is the ask)
    for k, r in results.items():
        if not (r["drive"]["torque_ok"] and r["drive"]["speed_ok"]):
            problems.append(f"{k}: drive outside motor envelope: {r['drive']}")

    # 6. motor sizing for the target is sane (positive, buildable holding torque)
    s = results["diff2"]["sized_for_target"]
    if not (0 < s["motor_holding_nm"] < mb.NEMA23_HT.holding_nm):
        problems.append(f"diff2 target holding torque implausible: {s}")

    # --- report ---
    print(f"scenario: SO-101 pulls a {load.payload_kg}kg part @ {load.ee_reach_x*100:.0f}cm reach, "
          f"{load.ee_height*100:.0f}cm high (target hold {TARGET_N}N)\n")
    for k, r in results.items():
        h = r["hold"]
        print(f"  {r['design']:26s} fwd {h['limit_N']:5.1f}N ({h['binding']:9s}) | "
              f"lat {r['lateral_hold_N']:5.1f}N | margin {h['static_margin_mm']:5.1f}mm -> "
              f"{'PASS' if r['pass'] else 'FAIL'}")
    print(f"\n  motor to resist {TARGET_N}N on diff2: wheel {results['diff2']['sized_for_target']['wheel_holding_nm']}Nm "
          f"-> {results['diff2']['sized_for_target']['motor_holding_nm']}Nm at the shaft "
          f"(NEMA17 has {mb.NEMA17.holding_nm}Nm)")

    if problems:
        for p in problems:
            print("FAIL:", p)
        return 1
    print("\nPASS: tip-over binds (not motor lock); passive mecanum flagged; a buildable base clears the pick")
    return 0


if __name__ == "__main__":
    sys.exit(main())
