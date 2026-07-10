"""ir_local.py — software-mfg's project-specific feature-IR samples.

featuretree's `ir` (the neutral CAD DSL + emitters) is composed BY REFERENCE from the
../featuretree sibling repo — this module does NOT fork it. It imports the library and
adds the one sample that belongs to THIS project: `coupling_plate`, the real tool-changer
coupling blank (cf. parts/_coupling.py). Everything else — the DSL builders (sketch/pad/
pocket/fillet/part), update_from_freecad, and the library's own SAMPLES — comes straight
from the sibling, so upstream changes flow through automatically.

  from ir_local import IR, SAMPLES     # IR = the sibling library; SAMPLES = lib + local
"""

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


# the library's samples + this project's own, in one dict
SAMPLES = {**IR.SAMPLES, "coupling_plate": coupling_plate}
