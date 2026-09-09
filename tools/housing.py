#!/usr/bin/env python3
"""MEWP tracker enclosure - parametric Blender model (run headless).

Driven by the BOARD's measured facts, not guesses:
  board 82 x 62 x 1.6, M3 holes H1(3.5,3.5) H2(78.5,3.5) H3(3.5,58.5)
  H4(78.5,58.5) H5(23.5,55)  -> five bosses (F-18: H5 gets its boss here)
  J1 = XUNPU MX3.0-12PZZ VERTICAL (top-entry) at (7.5, 30) rot 90:
     the plug mates from above INSIDE the cavity -> harness exits through
     an M16 cable gland in the -X wall (16.5 hole), no open aperture
  external active GNSS antenna  -> SMA bulkhead hole, +X wall (RF corridor)
  LTE FPC antenna mounted in the LID with MECHANICAL retention (F-23):
     two clamp bosses + a strap channel, adhesive alone not accepted
  SIM service: lid-off access (X1 push-push faces up)
  product spec: housing light-coloured (thermal); operating -20..+70 C
  IP intent: perimeter gasket groove in the lid skirt

Run:  blender -b -P tools/housing.py
Outputs: docs/housing/{base,lid}.stl, docs/housing/housing-*.png,
         docs/housing/housing.blend
"""
import math
import os

import bpy

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "docs", "housing")
os.makedirs(OUT, exist_ok=True)

# ---------------- parameters (mm) ------------------------------------------
BW, BH = 82.0, 62.0                 # board
MARGIN = 1.5                        # cavity margin around the board
WALL = 2.5
FLOOR = 2.5
STANDOFF = 5.0                      # board sits this high above the floor
ABOVE = 22.0                        # J1 vertical Micro-Fit mated + wire bend
LID_PLATE = 2.5
LID_POCKET = 3.5                    # lid interior for the FPC + clips
HOLES = [(3.5, 3.5), (78.5, 3.5), (3.5, 58.5), (78.5, 58.5), (23.5, 55.0)]

IX0, IY0 = -MARGIN, -MARGIN                     # cavity inner rect
IX1, IY1 = BW + MARGIN, BH + MARGIN
OX0, OY0 = IX0 - WALL, IY0 - WALL               # outer rect
OX1, OY1 = IX1 + WALL, IY1 + WALL
BASE_H = FLOOR + STANDOFF + 1.6 + ABOVE         # 20.1 total

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.length_unit = 'MILLIMETERS'


def cube(name, x0, y0, z0, x1, y1, z1):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.object
    o.name = name
    o.scale = ((x1 - x0), (y1 - y0), (z1 - z0))
    o.location = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    bpy.ops.object.transform_apply(scale=True, location=True)
    return o


def cyl(name, x, y, z0, z1, r, axis='Z'):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=(z1 - z0),
                                        vertices=48)
    o = bpy.context.object
    o.name = name
    if axis == 'Z':
        o.location = (x, y, (z0 + z1) / 2)
    elif axis == 'X':
        o.rotation_euler = (0, math.pi / 2, 0)
        o.location = ((z0 + z1) / 2, x, y)
    bpy.ops.object.transform_apply(rotation=True, location=True)
    return o


def boolop(target, tool, op):
    m = target.modifiers.new(name=op, type='BOOLEAN')
    m.operation = op
    m.object = tool
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(tool, do_unlink=True)


# ---------------- BASE -------------------------------------------------------
base = cube("base_outer", OX0, OY0, 0, OX1, OY1, BASE_H)
cav = cube("cavity", IX0, IY0, FLOOR, IX1, IY1, BASE_H + 1)
boolop(base, cav, 'DIFFERENCE')

# five M3 bosses (heat-set inserts: bore 4.0, boss OD 8)
for hx, hy in HOLES:
    b = cyl("boss", hx, hy, FLOOR, FLOOR + STANDOFF, 4.0)
    boolop(base, b, 'UNION')
    d = cyl("bore", hx, hy, FLOOR + STANDOFF - 6.0, FLOOR + STANDOFF + 0.1, 2.0)
    boolop(base, d, 'DIFFERENCE')

# J1 is TOP-ENTRY (vertical Micro-Fit at (7.5,30)): the harness plugs in
# from above inside the cavity and exits through an M16 cable gland in the
# -X wall (16.5 clearance hole, gland clamps the 2.5 wall). External boss
# ring gives the gland nut a flat seat.
gz = FLOOR + STANDOFF + 1.6 + 9.4           # hole centre, clear of the board
                                            # and boss top below the lid seat
gboss = cyl("gland_boss", 30.0, gz, OX0 - 2.0, OX0 + WALL, 12.0, axis='X')
boolop(base, gboss, 'UNION')
gh = cyl("gland_hole", 30.0, gz, OX0 - 3.0, IX0 + 1, 8.25, axis='X')
boolop(base, gh, 'DIFFERENCE')

# SMA bulkhead, +X wall: antennas are INTERNAL (lid FPC LTE + GNSS patch,
# U.FL) - the SMA is the handoff's "drill option for steel installs" where a
# U.FL->SMA pigtail feeds an external antenna instead. One hole drilled
# (GNSS-or-LTE, installer's choice), a second boss with a 1 mm pilot dimple
# stays sealed until needed.
sma_z = FLOOR + STANDOFF + 1.6 + 6.0
sma = cyl("sma", 30.0, sma_z, OX1 - WALL - 1, OX1 + 1, 3.25, axis='X')
boolop(base, sma, 'DIFFERENCE')
sma2b = cyl("sma2_boss", 44.0, sma_z, OX1 - 1.0, OX1 + 1.5, 6.0, axis='X')
boolop(base, sma2b, 'UNION')
sma2p = cyl("sma2_pilot", 44.0, sma_z, OX1 + 0.5, OX1 + 2.0, 0.5, axis='X')
boolop(base, sma2p, 'DIFFERENCE')

# external corner posts for the lid screws (M3 self-tap, 2.5 pilot)
POSTS = [(OX0 - 3.0, OY0 - 3.0), (OX1 + 3.0, OY0 - 3.0),
         (OX0 - 3.0, OY1 + 3.0), (OX1 + 3.0, OY1 + 3.0)]
for px, py in POSTS:
    p = cyl("post", px, py, 0, BASE_H, 4.5)
    boolop(base, p, 'UNION')
    d = cyl("pilot", px, py, BASE_H - 12.0, BASE_H + 0.1, 1.25)
    boolop(base, d, 'DIFFERENCE')

# mounting flanges (MEWP chassis, M5 slots) on the +-Y ends
for fy0, fy1 in ((OY0 - 14.0, OY0), (OY1, OY1 + 14.0)):
    f = cube("flange", OX0 + 8, fy0, 0, OX1 - 8, fy1, 4.0)
    boolop(base, f, 'UNION')
    for sx in (OX0 + 20, OX1 - 20):
        s = cube("slot", sx - 3, (fy0 + fy1) / 2 - 5.5, -1,
                 sx + 3, (fy0 + fy1) / 2 + 5.5, 5)
        boolop(base, s, 'DIFFERENCE')

# ---------------- LID --------------------------------------------------------
LZ0 = BASE_H
lid = cube("lid_plate", OX0, OY0, LZ0, OX1, OY1, LZ0 + LID_PLATE + LID_POCKET)
pocket = cube("lid_pocket", IX0, IY0, LZ0, IX1, IY1,
              LZ0 + LID_POCKET)
boolop(lid, pocket, 'DIFFERENCE')
# gasket groove in the lid rim (2 wide x 1.5 deep, midline of the wall)
g_off = WALL / 2
groove_outer = cube("go", IX0 - g_off - 1.0, IY0 - g_off - 1.0, LZ0,
                    IX1 + g_off + 1.0, IY1 + g_off + 1.0, LZ0 + 1.5)
groove_inner = cube("gi", IX0 - g_off + 1.0, IY0 - g_off + 1.0, LZ0 - 1,
                    IX1 + g_off - 1.0, IY1 + g_off - 1.0, LZ0 + 2)
boolop(groove_outer, groove_inner, 'DIFFERENCE')
boolop(lid, groove_outer, 'DIFFERENCE')

# F-23: MECHANICAL retention for the lid-mounted LTE FPC antenna - two clamp
# bosses and a strap channel across the FPC bay (adhesive alone rejected).
# FPC bay sits over the RF corridor half of the lid.
for cx in (55.0, 75.0):
    c = cyl("clamp", cx, 31.0, LZ0, LZ0 + LID_POCKET, 3.0)
    boolop(lid, c, 'UNION')
    d = cyl("clamp_pilot", cx, 31.0, LZ0, LZ0 + LID_POCKET + 0.1, 1.1)
    boolop(lid, d, 'DIFFERENCE')
strap = cube("strap_rib_a", 48.0, 20.0, LZ0, 50.0, 42.0, LZ0 + 1.6)
boolop(lid, strap, 'UNION')
strap2 = cube("strap_rib_b", 78.0, 20.0, LZ0, 80.0, 42.0, LZ0 + 1.6)
boolop(lid, strap2, 'UNION')

# lid corner screw holes (into the base posts), countersunk
for px, py in POSTS:
    ear = cyl("lid_ear", px, py, LZ0, LZ0 + LID_PLATE + LID_POCKET, 4.5)
    boolop(lid, ear, 'UNION')
    h = cyl("lid_hole", px, py, LZ0 - 1, LZ0 + LID_POCKET + LID_PLATE + 1, 1.7)
    boolop(lid, h, 'DIFFERENCE')

# ---------------- material / render / export --------------------------------
mat = bpy.data.materials.new("light_grey")     # product spec: light-coloured
mat.diffuse_color = (0.85, 0.85, 0.82, 1.0)
for o in (base, lid):
    o.data.materials.append(mat)

# exports
for o, nm in ((base, "base"), (lid, "lid")):
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    try:
        bpy.ops.wm.stl_export(filepath=os.path.join(OUT, nm + ".stl"),
                              export_selected_objects=True)
    except Exception:
        bpy.ops.export_mesh.stl(filepath=os.path.join(OUT, nm + ".stl"),
                                use_selection=True)

# renders: iso views, workbench engine (reliable headless)
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.render.resolution_x, scene.render.resolution_y = 1400, 1000
cam = bpy.data.cameras.new("cam")
camo = bpy.data.objects.new("cam", cam)
scene.collection.objects.link(camo)
scene.camera = camo


def look_at(o, target):
    from mathutils import Vector
    d = Vector(target) - o.location
    o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


center = ((OX0 + OX1) / 2, (OY0 + OY1) / 2, BASE_H / 2)
views = [("iso", (200, -160, 160)), ("front", (40, -260, 40)),
         ("top", (40, 34, 300))]
# separate lid for the exploded iso
lid.location.z += 25.0
for nm, pos in views:
    camo.location = pos
    look_at(camo, center)
    scene.render.filepath = os.path.join(OUT, f"housing-{nm}.png")
    bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "housing.blend"))
print("HOUSING_DONE")
