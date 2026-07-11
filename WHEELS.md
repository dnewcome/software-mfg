# Omni Wheels — source analysis + what we built

Two things kept getting conflated, so this file separates them:

1. **The real wheels** — the downloaded XRP Kiwi-bot files, and what measuring them told us.
2. **What we built** — the parametric / IR models in this repo (which are *approximations* of, or
   *unrelated to*, the real wheel).

---

## 1. The real wheel (source files)

Everything downloaded is the **XRP "Omni-Directional Kiwi Bot" drive base** kit (`~/Downloads/
xrp-omni-directional-kiwi-bot-drive-base-model_files/`). It ships in two forms:

| file | what it is | key facts |
|------|-----------|-----------|
| `kiwi-omni-directional-bot-v10.step` | **the merged whole-bot STEP** — the entire drive base as one file | 215 × 195 × 70 mm, **84 solids**; the thing you'd have to split to reverse-engineer to parts |
| `Omni Wheel/omni-wheel-shell.step` (= `kiwi-… - Omni Wheel Shell.step`) | **the one actual standalone wheel STEP** (B-rep) | OD 68, width ~39, ~43 k mm³ |
| `Omni Wheel/omni-wheel-shell.stl` | the same wheel as a **mesh** | 55 k triangles — no B-rep, no features |
| `omni-wheel-chassis.stl`, `…-drive-base-….pdf` | chassis + build instructions | — |
| `~/Downloads/omniwheel-edited.step` | **your hand-edit of the wheel** | OD 68, width 37.6, **36 k mm³** (hollowed further) — the current target |

So there is **one wheel** (XRP, OD 68, 8 rollers) that exists as: a mesh, a standalone B-rep, a
part inside the merged bot, and your edited B-rep.

## 2. Analysis — what measuring the XRP wheel told us

Measured off `Omni Wheel Shell.step` (OCCT face classification; download's axis = Y):

- **OD 68**, width ~39, ~43 k mm³ solid (the shell; your edit hollows it to ~36 k).
- **Rollers: 8 total = 2 rows × 4, staggered 45°.** Found via 16 × Ø3.2 pin bores → 8 coaxial
  fork-pairs; roller-axis pitch **MOUNT_R ≈ 30**.
- **Continuous contact** — *empirically*: 100 % OD coverage, 0° gap. Per-roller arc ≈ **±28°**,
  because the barrels **overhang their pins ~2.6×** (pin span implied only ±11°). This is why our
  old analytic continuity check (`atan(HALF_L/MOUNT_R) ≥ 90/N`) was wrong — see the geometric
  continuity check in `scripts/omni_check.py`.
- **Drive:** Feetech **STS3215** servo. Horn from datasheet **ST-3215-C047** §11: horn OD Ø19.95,
  hub Ø9, bolt circle **Ø14**, **4 × Ø3.2 (M3)**, spline **25T / Ø5.9**, retaining screw M3×6.
- **Format reality:** the STL is a mesh (rejected by any B-rep tool); the STEP is B-rep but the
  wheel is a **revolve + a circular pattern of freeform (bspline/sphere/torus) roller pockets** —
  *not* the 2.5D-prismatic class, so automatic STEP→IR recognition returns UNSUPPORTED (correct).

## 3. What we built (models in this repo)

Two of the three models are now the XRP wheel (a **functional** parametric assembly and an
**editable-tree** IR); #3 is a separate solid drive wheel.

| # | model | files | rollers / OD | relation to the XRP wheel |
|---|-------|-------|--------------|---------------------------|
| 1 | **parametric omni** (functional) | `parts/_omni.py` + `omni_hub.py` + `omni_roller.py` | **2×4 = 8, OD 70** | **the XRP wheel**, grey-box parametric: real barrel-roller + carve-out hub STLs that assemble, spin free, and are gated by `make omni-check`. Retargeted from the earlier OD60/10-roller photo wheel. |
| 2 | **`kiwi_wheel` (IR)** | `scripts/ir_local.py:kiwi_wheel` → `exports/freecad/kiwi_wheel.FCStd` | **2×4 = 8, OD 70** | **the XRP wheel** on the SAME integer design as #1 (OD 70, MOUNT_R 25, Ø20 rollers) — a solid-envelope editable FreeCAD tree + STS3215 mount (no discrete rollers). |
| 3 | **`base_wheel`** | `parts/base_wheel.py` | solid tire, no rollers | a **from-scratch** diff-drive drive wheel — not omni. |

**The XRP wheel's design closes on clean integers** (#1): a **Ø70 wheel arc** (R_EFF 35) with **Ø20
barrel rollers** (barrel_max 10) 30 mm long, so **MOUNT_R = R_EFF − 10 = 25** (= the measured pin
pitch), **4/row × 2 staggered** rows. Coverage `atan(15/25)=31° > 22.5°` → continuous; the hub blank
radius derives from the roller length so the pin snap-lip has material (`CLEAR_R =
min(R_EFF−1, hypot(MOUNT_R, HALF_L+3))`). Built OD 70, width 46 (real ≈ 39 — the model separates the
rows slightly more than the real nested wheel).

**#2 (`kiwi_wheel`) is a hand-authored IR reproduction**, not a recognizer output. It is the wheel's
**body-of-revolution envelope + roller cavities**, i.e. a *solid* approximation (~83 k mm³ with the
servo mount) — the IR cannot express the real wheel's hollow spoked interior. What matches the real
wheel exactly: **OD 68, 8 staggered roller pockets, MOUNT_R 30**, and the STS3215 mount. It adds a
servo-drive interface not in the download: a Ø22 standoff boss (roller-to-servo clearance), a Ø20.5
horn recess + Ø14/4×M3 bolt circle, and a back-access counterbore (short screws).

## 4. Tooling this drove (in ../featuretree, by reference)

Reverse-engineering the XRP wheel is what forced these featuretree features into existence:

- **`revolve`** + **XZ-plane profile sketches** — bodies of revolution (the wheel disc/hub).
- **`polar_pocket`** — a ring of tangent cylindrical pockets (the roller cavities).
- **`step_recognize`** — STEP→IR for the 2.5D-prismatic class, with fail-loud verification (it
  correctly refuses this wheel).
- **geometric continuity** (`scripts/omni_check.py`) — measure OD coverage on the assembled wheel
  instead of the fragile analytic proxy.

## 5. Status (2026-07-11)

- **#1 (functional) and #2 (IR)** are now the SAME XRP wheel — both OD 70, MOUNT_R 25, Ø20 rollers,
  2×4 staggered, **40 mm roller width + an 8 mm STS3215 standoff boss = 48 mm**. #1 has real
  spinning rollers + carve-out hub; #2 is the editable FreeCAD-tree envelope. Both carry the servo
  mount (horn recess + Ø14/4×M3 bolt circle + back-access counterbore).
- **Width**: nested to 40 mm (rollers) via `ROW_SEP_HALF=9.5`, still 0 interference / continuous.
- **FreeCAD visibility**: featuretree's `fc_build.py` now injects a `GuiDocument.xml` into each
  `.FCStd` (freecadcmd writes none), so files open with the solid visible instead of all-hidden.
- **Remaining gap**: #2 is still a *solid* approximation (no hollow spoked interior / discrete
  rollers) — inherent to the IR. #1 is the printable, functional wheel.
