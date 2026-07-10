#!/usr/bin/env python3
"""ir_solid.py — one feature-IR, BOTH representations, from a single source.

The featuretree cell (../featuretree, composed by reference) now has a build123d backend
(b3d_emit), so the SAME IR that emits an editable FreeCAD/Onshape tree also renders a
watertight build123d solid — no second, hand-maintained model. build123d and FreeCAD share
the OpenCASCADE kernel, so the geometry is identical (plate 11497.3 mm^3 either way).

    python scripts/ir_solid.py [sample]     # render an IR sample -> exports/freecad/<name>.b3d.stl
    python scripts/ir_solid.py --check       # gate: watertight solid + volume regression (no FreeCAD)
    python scripts/ir_solid.py --parity      # additionally diff build123d vs the LIVE FreeCAD backend
"""

import json
import sys
import tempfile
from pathlib import Path

import trimesh

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from freecad_cmd import featuretree_root, freecadcmd_path, lib_script, run_in_freecad  # noqa: E402
from ir_local import SAMPLES  # noqa: E402

sys.path.insert(0, str(featuretree_root()))
from b3d_emit import emit  # noqa: E402  (the featuretree build123d backend)
from build123d import export_stl  # noqa: E402

OUT = ROOT / "exports" / "freecad"
# regression anchors = the FreeCAD-backend volumes (Δ=0.0 to build123d, same OCCT kernel).
# These guard cross-backend equivalence WITHOUT needing FreeCAD in `make check`.
EXPECT = {"plate": 11497.3, "poly": 4768.6, "coupling_plate": 10693.5}


def emit_solid(name):
    """Render IR sample `name` to a (build123d Solid, result dict)."""
    return emit(SAMPLES[name]())


def _watertight_single(part):
    f = tempfile.mktemp(suffix=".stl")
    export_stl(part, f)
    m = trimesh.load(f)
    Path(f).unlink()
    return m.is_watertight, len(m.split(only_watertight=False))


def _fc_volume(spec):
    OUT.mkdir(parents=True, exist_ok=True)
    irj, fcstd = OUT / "parity.ir.json", OUT / "parity.FCStd"
    irj.write_text(json.dumps(spec))
    proc = run_in_freecad(lib_script("fc_build.py"), {"FC_IR": irj, "FC_OUT": fcstd})
    line = next((l for l in proc.stdout.splitlines() if l.startswith("RESULT:")), None)
    if line is None:
        raise RuntimeError((proc.stdout or "")[-500:] + (proc.stderr or "")[-500:])
    return json.loads(line[len("RESULT:"):])["volume"]


def demo(sample):
    part, res = emit_solid(sample)
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{sample}.b3d.stl"
    export_stl(part, str(out))
    wt, bodies = _watertight_single(part)
    print(f"one IR -> build123d solid: {sample} = {res['volume']} mm^3 "
          f"(watertight={wt}, bodies={bodies}) -> {out.relative_to(ROOT)}")
    print("tree:")
    for label, tid in res["tree"]:
        print(f"  {label:16} {tid}")
    print("params:", json.dumps(res["params"]))
    return 0


def check(parity=False):
    problems = []
    vols = {}
    for name in SAMPLES:
        part, res = emit_solid(name)
        vols[name] = res["volume"]
        wt, bodies = _watertight_single(part)
        if not wt or bodies != 1:
            problems.append(f"{name}: build123d solid not single+watertight (wt={wt}, bodies={bodies})")
        if res["volume"] <= 0:
            problems.append(f"{name}: non-positive volume {res['volume']}")
        exp = EXPECT.get(name)
        if exp is not None and abs(res["volume"] - exp) > 1.0:
            problems.append(f"{name}: volume {res['volume']} drifted from anchor {exp}")

    parity_note = "not run (pass --parity)"
    if parity:
        try:
            freecadcmd_path()
        except FileNotFoundError as e:
            parity_note = f"SKIPPED — {e}"
        else:
            diffs = []
            for name in SAMPLES:
                fcv = _fc_volume(SAMPLES[name]())
                d = abs(fcv - vols[name])
                diffs.append(f"{name} Δ{d:.2f}")
                if d > 1.0:
                    problems.append(f"{name}: build123d {vols[name]} != FreeCAD {fcv} (Δ{d:.2f})")
            parity_note = "OK (" + ", ".join(diffs) + ")"

    print("one IR -> both:  build123d " + ", ".join(f"{k}={v}" for k, v in vols.items()))
    print("  vs FreeCAD:    " + parity_note)
    if problems:
        for p in problems:
            print("FAIL:", p)
        return 1
    print("PASS: the same IR renders a watertight build123d solid, volumes matched to the "
          "kernel-shared FreeCAD tree")
    return 0


def main():
    args = sys.argv[1:]
    if "--check" in args or "--parity" in args:
        return check(parity="--parity" in args)
    sample = next((a for a in args if not a.startswith("-")), "coupling_plate")
    return demo(sample)


if __name__ == "__main__":
    sys.exit(main())
