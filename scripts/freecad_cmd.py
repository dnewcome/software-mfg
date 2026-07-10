"""freecad_cmd.py — software-mfg's glue to the featuretree cell + FreeCAD's own Python.

Two project-local concerns that do NOT belong in the featuretree library itself:

  1. featuretree_root() — locate the featuretree cell, composed BY REFERENCE from the
     ../featuretree sibling repo (declared in cells.yaml), never forked into this tree.
     Override with FEATURETREE_ROOT. This is the same compose-don't-fork pattern as
     ../wirebender and ../so101-lab.
  2. run_in_freecad() — drive featuretree's fc_build.py / fc_read.py under FreeCAD's OWN
     headless interpreter (freecadcmd, Python 3.11), exactly like the wirebender cell runs
     under its own venv. Find (or extract once, cached) the AppImage's freecadcmd.
     Override with FREECAD_CMD or FREECAD_APPIMAGE.
"""

import os
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_APPIMAGE = "/opt/FreeCAD_1.0.2-conda-Linux-x86_64-py311.AppImage"
CACHE = Path.home() / ".cache" / "software-mfg" / "freecad"


def featuretree_root() -> Path:
    """The featuretree cell's checkout (../featuretree by default; from cells.yaml).
    Composed by reference — clone it with `git clone git@github.com:dnewcome/featuretree.git`
    next to this repo, or set FEATURETREE_ROOT."""
    env = os.environ.get("FEATURETREE_ROOT")
    if env:
        base = Path(env)
    else:
        cfg = yaml.safe_load((ROOT / "cells.yaml").read_text()).get("cells", {}).get("featuretree", {})
        base = (ROOT / cfg.get("path", "../featuretree")).resolve()
    if not (base / "ir.py").exists():
        raise FileNotFoundError(
            f"featuretree cell not found at {base}. It is composed by reference, not vendored — "
            "clone it beside this repo:\n"
            "    git clone git@github.com:dnewcome/featuretree.git ../featuretree\n"
            "(or set FEATURETREE_ROOT / edit cells.yaml).")
    return base


def lib_script(name: str) -> Path:
    """Path to one of featuretree's freecadcmd scripts (fc_build.py / fc_read.py)."""
    return featuretree_root() / name


def freecadcmd_path() -> str:
    env = os.environ.get("FREECAD_CMD")
    if env and Path(env).exists():
        return env
    for p in ("/tmp/squashfs-root/usr/bin/freecadcmd",
              str(CACHE / "squashfs-root/usr/bin/freecadcmd")):
        if Path(p).exists():
            return p
    appimage = os.environ.get("FREECAD_APPIMAGE", DEFAULT_APPIMAGE)
    if not Path(appimage).exists():
        raise FileNotFoundError(f"FreeCAD AppImage not found: {appimage} (set FREECAD_APPIMAGE)")
    CACHE.mkdir(parents=True, exist_ok=True)
    subprocess.run([appimage, "--appimage-extract"], cwd=str(CACHE), check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return str(CACHE / "squashfs-root/usr/bin/freecadcmd")


def run_in_freecad(script, env_vars=None, capture=True):
    """Run a script under freecadcmd. Pass data via env_vars, NOT argv — freecadcmd
    treats extra path args as documents to open, not script arguments. FC_LIBDIR
    defaults to the featuretree cell so the script's `import fc_common` resolves."""
    cmd = [freecadcmd_path(), str(script)]
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "FC_LIBDIR": str(featuretree_root())}
    if env_vars:
        env.update({k: str(v) for k, v in env_vars.items()})
    return subprocess.run(cmd, capture_output=capture, text=True, env=env)
