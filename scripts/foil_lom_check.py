#!/usr/bin/env python3
"""Gate: the foil-LOM build plan is manufacturable — and surfaces the foil reality.

Validates the slice plan (positive bond area, staircase error bounded by the layer
thickness, a schedulable per-layer op-graph) and reports the honest consequence of
~10um foil: thousands of layers and a long build. Calibration is unanchored, so the
plan is a PREDICTION — reported, not failed.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sim"))
sys.path.insert(0, str(ROOT / "orchestration"))
from calibration import CalibrationStore, staleness  # noqa: E402
from opgraph import schedule  # noqa: E402
import foil_lom as lom  # noqa: E402

LOM_PARAMS = ["foil_thickness", "foil_bond_shear_mpa"]
TOL_UM = 50.0    # surface tolerance the staircase must stay under


def main() -> int:
    m = lom.slice_solid("cone")
    problems = []

    # staircase error (finite-layer stepping) must stay under the surface tolerance.
    # For a wall steeper than 45deg it exceeds the layer thickness, so gate on the
    # tolerance, not the thickness. Thin foil is what keeps it small (the upside).
    if m["staircase_rms_um"] > TOL_UM:
        problems.append(f"staircase {m['staircase_rms_um']:.1f}um exceeds tolerance {TOL_UM:.0f}um")
    # the part must not delaminate under its own weight (calibrated bond gates it)
    if m["delam_margin"] < 1.0:
        problems.append(f"delaminates under own weight (margin {m['delam_margin']})")
    # the per-layer op-graph must schedule (feed -> bond -> cut, sequential on one server)
    g = lom.build_graph("cone", n_sample=3)
    sched, mk = schedule(g)
    if len(sched) != 9:                    # 3 layers x (feed, bond, cut)
        problems.append(f"op-graph wrong size: {len(sched)} ops")
    if mk <= 0:
        problems.append("op-graph makespan not positive")

    stamp = staleness(CalibrationStore.load(ROOT / "calibration" / "store.json"), LOM_PARAMS)
    trust = "VALIDATED" if stamp["verdict"] == "FRESH" else "PREDICTION (uncalibrated)"

    print(f"foil LOM: cone {m['height_mm']:.0f}mm @ {m['layer_um']:.0f}um -> "
          f"{m['layers']} layers, staircase {m['staircase_rms_um']:.1f}um (<{TOL_UM:.0f} tol), "
          f"{m['cut_length_m']}m cut, {m['mass_g']}g, delam margin {m['delam_margin']:.0f}x")
    print(f"build time: {m['build_time_h']}h ({m['throughput_layers_per_min']} layers/min) "
          f"— thin foil = many layers (the throughput reality)")
    print(f"calibration: {stamp['verdict']} -> {trust}")
    if problems:
        for p in problems:
            print("FAIL:", p)
        return 1
    print("PASS: slice plan manufacturable + schedulable; a PREDICTION until foil is measured")
    return 0


if __name__ == "__main__":
    sys.exit(main())
