"""ir_local.py — software-mfg's project-specific feature-IR samples.

featuretree's `ir` (the neutral CAD DSL + emitters) is composed BY REFERENCE from the
../featuretree sibling repo — this module does NOT fork it. It imports the library and
adds the one sample that belongs to THIS project: `coupling_plate`, the real tool-changer
coupling blank (cf. parts/_coupling.py). Everything else — the DSL builders (sketch/pad/
pocket/fillet/part), update_from_freecad, and the library's own SAMPLES — comes straight
from the sibling, so upstream changes flow through automatically.

  from ir_local import IR, SAMPLES     # IR = the sibling library; SAMPLES = lib + local
"""

import math
import sys

from freecad_cmd import featuretree_root

sys.path.insert(0, str(featuretree_root()))
import ir as IR  # noqa: E402  (the featuretree library, composed by reference)

# re-export the library's round-trip helper so callers need one import
update_from_freecad = IR.update_from_freecad


def coupling_plate():
    """The real tool-changer coupling blank (cf. parts/_coupling.py): a Ø50x6 disc with a
    Ø12 central bore + 3 M3 mounting holes, a filleted top rim, and a bore counterbore.

    The fillet selects the disc's top outer edge by QUERY (not a stored kernel edge id) and
    the counterbore sketch is attached to the top face by query — so both survive edits and
    rebuilds. A real project part, round-tripped through FreeCAD by name.
    """
    import math
    bolts = [(round(21 * math.cos(math.radians(a)), 4),
              round(21 * math.sin(math.radians(a)), 4)) for a in (30, 150, 270)]
    return IR.part(
        "coupling_plate",
        IR.sketch("disc_outline", "XY", circles=[(0, 0, 25)]),
        IR.pad("disc", "disc_outline", length=6),
        IR.fillet("rim_round", radius=1.0, select={"circles": "top_outer"}),
        IR.sketch("holes", "XY", circles=[(0, 0, 6)] + [(x, y, 1.7) for x, y in bolts]),
        IR.pocket("drill", "holes", through=True),
        # counterbore recess around the bore, drilled from the TOP FACE (face-attached
        # sketch — the face is chosen by query, then coords map into its local frame)
        IR.sketch("recess_sk", circles=[(0, 0, 9)], on={"face_of": "drill", "side": "top"}),
        IR.pocket("recess", "recess_sk", through=False, length=1.5),
    )


def kiwi_wheel():
    """The XRP omni wheel as an editable FreeCAD tree, on the SAME integer design as the functional
    parametric wheel (parts/_omni.py): a Ø70 wheel arc (R_EFF 35) with Ø20 barrel rollers at pitch
    MOUNT_R 25, 4/row × 2 rings staggered 45deg. Here it's the solid-envelope form: a 40 mm-wide
    disc (OD 70) + roller-cavity pockets + the STS3215 servo mount, revolved and polar-cut.

    Tree: Sketch -> Revolution -> two PolarPocket rings -> horn recess / hub bore / back-access /
    bolt circle. It's a SOLID approximation (no discrete rollers, no hollow spoked interior); what
    matches _omni exactly: OD 70, MOUNT_R 25, Ø20 rollers, 8 staggered pockets, the servo interface.
    """
    # Revolve profile (radius, axial): a Ø22 servo-side standoff boss (z=-28..-20) so the roller disc
    # (OD 70, z=-20..+20) clears the STS3215 body; the horn seats in the boss end.
    profile = [(1.1, -28.0), (11.0, -28.0), (11.0, -20.0), (35.0, -20.0), (35.0, 20.0), (1.1, 20.0)]
    # STS3215 horn bolt circle (ST-3215-C047): Ø14 BCD, 4× M3 clearance (Ø3.4).
    bcr = 7.0
    bolts = [(round(bcr * math.cos(math.radians(a)), 4), round(bcr * math.sin(math.radians(a)), 4))
             for a in (45, 135, 225, 315)]
    return IR.part(
        "kiwi_wheel",
        IR.sketch("section", "XZ", polys=[profile]),
        IR.revolve("body", "section", angle=360.0),
        # roller cavities: Ø20 rollers + clearance (r11), 30 mm long, at MOUNT_R 25, rows z=±9.5 staggered
        IR.polar_pocket("rollers_a", radius=11.0, length=32.0, mount_r=25.0, z=-9.5, count=4, phase=0.0),
        IR.polar_pocket("rollers_b", radius=11.0, length=32.0, mount_r=25.0, z=9.5, count=4, phase=45.0),
        # --- servo-horn mount on the boss end (bottom, z=-28) ---
        IR.sketch("horn_recess_sk", circles=[(0, 0, 10.25)], on={"face_of": "body", "side": "bottom"}),
        IR.pocket("horn_recess", "horn_recess_sk", through=False, length=3.0),   # Ø20.5 horn seat
        IR.sketch("hub_bore_sk", circles=[(0, 0, 4.6)], on={"face_of": "body", "side": "bottom"}),
        IR.pocket("hub_bore", "hub_bore_sk", through=False, length=6.0),         # Ø9.2 clears the Ø9 hub
        # back-access counterbore (from the disc back, z=+20): short M3 screws
        IR.sketch("access_sk", circles=[(0, 0, 9.0)], on={"face_of": "body", "side": "top"}),
        IR.pocket("access", "access_sk", through=False, length=36.0),            # Ø18 down to z=-16
        IR.sketch("horn_bolts_sk", circles=[(x, y, 1.7) for x, y in bolts],
                  on={"face_of": "body", "side": "bottom"}),
        IR.pocket("horn_bolts", "horn_bolts_sk", through=True),                  # 4× M3, boss->access bore
    )


# the library's samples + this project's own, in one dict
SAMPLES = {**IR.SAMPLES, "coupling_plate": coupling_plate, "kiwi_wheel": kiwi_wheel}
