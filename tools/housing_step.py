# FreeCAD (freecadcmd) script: check / repair the housing STLs and write STEP.
#
# 1. Every STL must be a closed solid (what a slicer or CAD import needs).
#    Blender's booleans leave a few non-manifold facets on the lids; FreeCAD's
#    mesh repair (non-manifold removal, hole filling, normal harmonising) is
#    applied and ACCEPTED ONLY if the result is solid and its volume is within
#    0.5 % of the original - otherwise the file is left as it was and flagged.
# 2. STEP: the mesh becomes a faceted solid (every triangle a planar face,
#    coplanar faces merged). Written only if valid and volume-matched, for
#    quoting, CNC / 3D print and fit checks in any CAD tool; a moulder still
#    redraws the part with draft angles (docs/housing-notes.md, open items).
#
# Run:  freecadcmd tools/housing_step.py
import os

import Mesh
import Part

ROOT = "/home/david/pcb/.claude/worktrees/route-finish/docs/housing"
_here = globals().get("__file__")
if _here:
    ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(_here))), "docs", "housing")

for variant in ("internal", "external"):
    for part in ("base", "lid"):
        stl = os.path.join(ROOT, variant, f"{part}.stl")
        step = os.path.join(ROOT, variant, f"{part}.step")
        m = Mesh.Mesh(stl)
        v0 = m.Volume
        note = "closed as exported"
        if not m.isSolid() or m.hasNonManifolds():
            r = Mesh.Mesh(m)
            r.removeNonManifolds()
            r.fillupHoles(1000)
            r.removeDuplicatedPoints()
            r.removeDuplicatedFacets()
            r.fixIndices()
            r.harmonizeNormals()
            if r.isSolid() and not r.hasNonManifolds() and abs(r.Volume - v0) <= 0.005 * abs(v0):
                r.write(stl)
                m, note = r, f"repaired (volume {v0 / 1000:.2f} -> {r.Volume / 1000:.2f} cm3)"
            else:
                note = (f"NOT CLOSED - repair rejected (solid={r.isSolid()}, "
                        f"volume {v0 / 1000:.2f} -> {r.Volume / 1000:.2f} cm3)")
        shape = Part.Shape()
        shape.makeShapeFromMesh(m.Topology, 0.01)
        written = "no STEP"
        ok = False
        for build in (lambda: Part.makeSolid(shape), lambda: Part.makeSolid(shape).removeSplitter()):
            try:
                s = build()
            except Exception as e:          # noqa: BLE001 - OCC refuses some meshes
                written = f"no STEP ({e})"
                continue
            if s.isValid() and abs(s.Volume - m.Volume) <= 0.005 * abs(m.Volume):
                s.exportStep(step)
                written, ok = f"STEP {len(s.Faces)} faces", True
                break
            written = f"no STEP (solid valid={s.isValid()}, volume {s.Volume / 1000:.2f} cm3)"
        if not ok and os.path.exists(step):
            os.unlink(step)
        bb = m.BoundBox
        print(f"HOUSING_STEP {variant}/{part}: {note}; {written}; "
              f"{bb.XLength:.1f} x {bb.YLength:.1f} x {bb.ZLength:.1f} mm, {m.Volume / 1000:.1f} cm3")
