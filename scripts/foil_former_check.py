#!/usr/bin/env python3
"""Gate: the foil former's forward model is sound — and honest about calibration.

The wire-bender analog for foil. Validates that overbend hits target after
springback, that folds stay physically feasible, and that work-hardening makes a
re-bent crease spring back MORE (and eventually crack). Because no physical former
exists yet, the foil parameters are UNANCHORED — the gate reports that status (a
PREDICTION), and only FAILS on a broken model, not on being uncalibrated.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sim"))
from calibration import CalibrationStore, staleness  # noqa: E402
import foil_former as ff  # noqa: E402

FOIL_PARAMS = ["foil_springback_deg", "foil_workharden_gain"]


def main() -> int:
    problems = []

    # 1. overbend actually lands the target angle after springback
    for target in (45.0, 90.0, 120.0):
        cmd = ff.overbend_deg(target)
        achieved = cmd - ff.springback_deg(cmd)
        if abs(achieved - target) > 0.5:
            problems.append(f"overbend misses target: {target} -> achieved {achieved:.1f}")
        if cmd <= target:
            problems.append(f"overbend not > target at {target} (got {cmd:.1f})")

    # 2. work-hardening: re-bending one crease springs back more, then cracks
    sb0 = ff.springback_deg(90.0, reversals=0)
    sb2 = ff.springback_deg(90.0, reversals=2)
    if not sb2 > sb0:
        problems.append(f"work-hardening not monotonic (sb {sb0:.2f} -> {sb2:.2f})")
    if ff.crease_reuse_ok(ff.FOIL_CRACK_BENDS):
        problems.append("crack limit not enforced")

    # 3. the channel program forms a feasible profile
    r = ff.simulate("channel")
    if not all(b["feasible"] for b in r["bends"]):
        problems.append(f"channel has an infeasible fold (max cmd {r['max_command']} deg)")

    # 4. calibration status — honest, not fatal
    stamp = staleness(CalibrationStore.load(ROOT / "calibration" / "store.json"),
                      FOIL_PARAMS, {"bend_deg": 90, "r_over_t": 3})
    trust = "VALIDATED" if stamp["verdict"] == "FRESH" else "PREDICTION (uncalibrated)"

    print(f"foil former: channel = {r['n_bends']} folds, {r['profile_length']} mm stock, "
          f"overbend {r['max_command']} deg | springback 90deg: {sb0:.1f}->{sb2:.1f} "
          f"(0->2 reversals), cracks at {ff.FOIL_CRACK_BENDS}")
    print(f"calibration: {stamp['verdict']} -> {trust}  "
          f"(foil params anchored {stamp['age_builds']} builds ago)")
    if problems:
        for p in problems:
            print("FAIL:", p)
        return 1
    print("PASS: foil former forward model sound (springback + work-hardening); "
          "results are PREDICTIONS until a physical former is measured")
    return 0


if __name__ == "__main__":
    sys.exit(main())
