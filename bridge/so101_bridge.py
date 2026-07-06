"""so101_bridge.py — compose so101-lab (the hardware/execution cell) by reference.

so101-lab (../so101-lab) owns the real arms: lerobot drivers, calibration, and Placo
FK/IK on the SO-101 URDF (its trace_path.py already does poses -> placo IK -> joints).
software-mfg owns design-time: CAD, planning, CAM, the world model. This bridge lets the
sim pipeline USE so101-lab's kinematics WITHOUT forking it — the same read-only,
own-interpreter pattern as the wire bender (declared in cells.yaml).

Motion service, with a graceful fallback so every gate runs standalone:
  * real     = so101-lab Placo (orientation-aware, on the real URDF)  [needs its venv + URDF]
  * fallback = the built-in positional DLS IK (sim/ik.py)

The bridge PROBES cheaply (no network, no arm, no `uv` invocation) and reports which
backend is live — LIVE vs SIM, the same honesty as the calibration staleness stamp.

Frame note: targets are workcell-world xyz (arm base at the origin), which matches the
URDF base to first order. The residual world<->base transform is a hand-eye/base
CALIBRATION item (identity until measured) — the same sim-is-a-cache-of-reality idea.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "sim"))
sys.path.insert(0, str(ROOT / "orchestration"))


def _cell():
    cfg = yaml.safe_load((ROOT / "cells.yaml").read_text()).get("cells", {}).get("so101lab")
    if not cfg:
        return None
    base = (ROOT / cfg["path"]).resolve()
    return {"base": base,
            "python": base / cfg.get("python", ".venv/bin/python"),
            "urdf": base / cfg.get("urdf", "urdf/so101_new_calib.urdf")}


def probe() -> dict:
    """Cheap capability check — never touches the network or the arm."""
    c = _cell()
    if not c:
        return {"backend": "builtin", "reason": "no so101lab cell in cells.yaml", "cell": None}
    have_py = c["python"].exists()
    have_urdf = c["urdf"].exists() or bool(os.environ.get("SO101_URDF"))
    if have_py and have_urdf:
        return {"backend": "placo", "reason": "so101-lab venv + URDF present", "cell": c}
    missing = []
    if not have_py:
        missing.append("venv (uv sync --extra kin)")
    if not have_urdf:
        missing.append("URDF (./fetch_urdf.sh)")
    return {"backend": "builtin",
            "reason": "so101-lab present but " + " + ".join(missing) + " missing", "cell": c}


# Runs inside so101-lab's OWN interpreter (its lerobot + placo + URDF). Mirrors
# trace_path.solve_trajectory: seed each waypoint from the previous solution.
_RUNNER = r'''
import os, json
import numpy as np
from lerobot.model.kinematics import RobotKinematics
from so101_config import URDF_PATH, URDF_TARGET_FRAME
targets = json.loads(os.environ["BR_TARGETS"])
ow = float(os.environ.get("BR_ORIENT_W", "0.0"))
kin = RobotKinematics(URDF_PATH, target_frame_name=URDF_TARGET_FRAME)
q = np.array([0.0, -35.0, 45.0, -10.0, 0.0, 0.0])
out = []
for t in targets:
    T = np.eye(4); T[:3, 3] = t
    err = 1e9
    for _ in range(120):
        q = kin.inverse_kinematics(q, T, position_weight=1.0, orientation_weight=ow)
        err = float(np.linalg.norm(kin.forward_kinematics(q)[:3, 3] - np.array(t)) * 1000.0)
        if err < 0.3:
            break
    out.append({"q": [float(x) for x in q], "err_mm": err})
print("RESULT:" + json.dumps(out))
'''


def _solve_placo(cell, targets, orientation_weight):
    proc = subprocess.run(
        [str(cell["python"]), "-c", _RUNNER], cwd=str(cell["base"]),
        capture_output=True, text=True, timeout=120,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
             "BR_TARGETS": json.dumps([[float(x) for x in t] for t in targets]),
             "BR_ORIENT_W": str(orientation_weight)},
    )
    line = next((ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT:")), None)
    if line is None:
        raise RuntimeError(f"placo runner failed:\n{proc.stdout[-400:]}\n{proc.stderr[-400:]}")
    return json.loads(line[len("RESULT:"):])


def _solve_builtin(targets):
    import toolpath
    solve = toolpath.builtin_ik_solver()
    out = []
    for t in targets:
        q, err = solve(t)
        out.append({"q": q.tolist() if hasattr(q, "tolist") else list(q),
                    "err_mm": float(err) * 1000.0})
    return out


def solve_path(targets, orientation_weight=0.0, prefer="auto") -> dict:
    """Solve (x,y,z) tip targets -> joint waypoints via the best available backend.

    Returns {backend, status, waypoints:[{q, err_mm}], max_err_mm}. Never raises for a
    missing hardware cell — it falls back to the built-in solver and says so."""
    p = probe()
    backend = p["backend"] if prefer == "auto" else prefer
    if backend == "placo" and p["cell"]:
        try:
            wps = _solve_placo(p["cell"], targets, orientation_weight)
            status = f"LIVE placo (so101-lab): {p['reason']}"
        except Exception as e:
            wps, backend = _solve_builtin(targets), "builtin"
            status = f"SIM fallback (placo failed: {type(e).__name__}: {e})"
    else:
        wps, backend = _solve_builtin(targets), "builtin"
        status = f"SIM fallback: {p['reason']}"
    max_err = max((w["err_mm"] for w in wps), default=0.0)
    return {"backend": backend, "status": status, "waypoints": wps,
            "max_err_mm": round(max_err, 2)}


def status() -> str:
    p = probe()
    return f"motion backend: {p['backend'].upper()} — {p['reason']}"
