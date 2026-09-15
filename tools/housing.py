#!/usr/bin/env python3
"""MEWP tracker enclosure - parametric Blender model, TWO VARIANTS.

  internal  both antennas INSIDE, lid-mounted on their U.FL pigtails:
            LTE FPC (39.6 x 14.5) in a heat-staked bay, GNSS ceramic patch
            (25 x 25 x 6.5) in a corner-tab pocket. Walls are solid; the two
            SMA positions exist only as sealed pilot dimples (drill option).
  external  steel-cabinet build: two O-ring sealed SMA bulkhead jacks in the
            +X wall (GNSS + LTE) feeding external antennas; plain shallow lid.

Common (both variants): sealed body to IP67 intent -
  perimeter O-ring cord (d 2.0) in a lid groove, compressed by a tongue rib on
  the base wall top; 6 lid screws OUTSIDE the seal line; M16 IP68 cable gland
  for the harness (J1 is top-entry, so no open aperture); M12 ePTFE vent plug
  for pressure equalisation over -20..+70 C; 5 M3 bosses (F-18 H5 boss);
  M5-slotted chassis flanges; light-coloured ASA.

Driven by the BOARD's measured facts:
  board 82 x 62 x 1.6, M3 holes H1(3.5,3.5) H2(78.5,3.5) H3(3.5,58.5)
  H4(78.5,58.5) H5(23.5,55); J1 vertical Micro-Fit at (7.5,30) rot 90;
  U.FL AF1 (LTE) at (79.3,10.2), AF2 (GNSS) at (79.3,48.5); SIM X1 at
  (53.7,52.4) faces up (lid-off service).
Antenna clearances (docs/installation-sheet.md 5a, MANDATORY):
  LTE FPC > 5 mm from the main PCB; GNSS patch >= 3 mm from the enclosure
  wall, >= 10 mm from tall metal; > 40 dB isolation (kept far apart); no metal
  fixings over the antenna areas -> retention is plastic tabs / heat stakes,
  never screws (F-23: adhesive alone rejected).

Run:  blender -b -P tools/housing.py -- internal
      blender -b -P tools/housing.py -- external
Outputs: docs/housing/<variant>/{base,lid}.stl, housing.blend, housing-*.png
"""
import math
import os
import sys

import bpy

VARIANT = "internal"
if "--" in sys.argv:
    VARIANT = sys.argv[sys.argv.index("--") + 1]
VARIANT = os.environ.get("HOUSING_VARIANT", VARIANT).lower()
assert VARIANT in ("internal", "external"), VARIANT
INTERNAL = VARIANT == "internal"

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "docs", "housing", VARIANT)
os.makedirs(OUT, exist_ok=True)

# ---------------- parameters (mm) ------------------------------------------
BW, BH = 82.0, 62.0                 # board
MARGIN = 1.5                        # cavity margin around the board
WALL = 2.5
FLOOR = 2.5
STANDOFF = 5.0                      # board sits this high above the floor
ABOVE = 22.0                        # J1 vertical Micro-Fit mated + wire bend
LID_PLATE = 2.5
# lid interior: the internal variant must swallow the 6.5 mm patch plus its
# tabs; the external lid only needs a skirt for the seal.
LID_POCKET = 8.0 if INTERNAL else 3.5
HOLES = [(3.5, 3.5), (78.5, 3.5), (3.5, 58.5), (78.5, 58.5), (23.5, 55.0)]

IX0, IY0 = -MARGIN, -MARGIN                     # cavity inner rect
IX1, IY1 = BW + MARGIN, BH + MARGIN
OX0, OY0 = IX0 - WALL, IY0 - WALL               # outer rect
OX1, OY1 = IX1 + WALL, IY1 + WALL
BOARD_TOP = FLOOR + STANDOFF + 1.6
BASE_H = BOARD_TOP + ABOVE                      # 31.1 total

# seal: d2.0 silicone cord in a 2.4 x 1.6 groove (82 % fill) pressed by a
# 1.0 x 0.8 tongue on the base wall top -> ~20 % cord compression
GROOVE_W, GROOVE_D = 2.4, 1.6
TONGUE_W, TONGUE_H = 1.0, 0.8
SEAL_MID = WALL / 2                             # seal line = wall midline
SX0, SY0 = OX0 + SEAL_MID, OY0 + SEAL_MID       # seal-line rectangle
SX1, SY1 = OX1 - SEAL_MID, OY1 - SEAL_MID

# antennas (installation-sheet.md 5a)
FPC_L, FPC_W, FPC_T = 39.6, 14.5, 0.3           # BW4GFNX39-15B1
PATCH, PATCH_H = 25.0, 6.5                      # BWGNSCNX25-25B1Y4L120
FPC_C = (56.0, 11.0)        # bay centre: toward the LTE U.FL corner (79.3,10.2)
PATCH_C = (68.0, 40.0)      # pocket centre: >= 3 mm off the +X wall, near AF2
WALL_CLR = 3.0              # patch to enclosure wall, mandatory minimum

# through-wall fittings
GLAND_HOLE_R = 8.25         # M16 x 1.5 IP68 gland, d16.5 clearance
GLAND_Y = 30.0              # in line with J1
VENT_HOLE_R = 6.1           # M12 x 1.5 ePTFE vent plug, d12.2 clearance
VENT_X = 20.0
SMA_HOLE_R = 3.25           # d6.5 for a 1/4-36 SMA bulkhead, O-ring sealed
SMA_YS = (30.0, 44.0)       # GNSS, LTE - 14 mm apart for the nut spanner

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.length_unit = 'MILLIMETERS'


def span(c, s, a, b):
    """Interval from c+s*a to c+s*b, sorted. s = +-1 picks the direction."""
    return tuple(sorted((c + s * a, c + s * b)))


def cube(name, x0, y0, z0, x1, y1, z1):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.object
    o.name = name
    o.scale = ((x1 - x0), (y1 - y0), (z1 - z0))
    o.location = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    bpy.ops.object.transform_apply(scale=True, location=True)
    return o


def cyl(name, x, y, z0, z1, r, axis='Z'):
    """Z: axis at (x,y) from z0..z1.  X: axis along X at (y=x, z=y), from
    x=z0..z1.  Y: axis along Y at (x=x, z=y), from y=z0..z1."""
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=(z1 - z0),
                                        vertices=48)
    o = bpy.context.object
    o.name = name
    if axis == 'Z':
        o.location = (x, y, (z0 + z1) / 2)
    elif axis == 'X':
        o.rotation_euler = (0, math.pi / 2, 0)
        o.location = ((z0 + z1) / 2, x, y)
    elif axis == 'Y':
        o.rotation_euler = (math.pi / 2, 0, 0)
        o.location = (x, (z0 + z1) / 2, y)
    bpy.ops.object.transform_apply(rotation=True, location=True)
    return o


def boolop(target, tool, op):
    m = target.modifiers.new(name=op, type='BOOLEAN')
    m.operation = op
    m.object = tool
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(tool, do_unlink=True)


def ring(name, x0, y0, x1, y1, z0, z1, w):
    """Rectangular ring of width w whose CENTRELINE is the rect x0..x1,y0..y1."""
    outer = cube(name, x0 - w / 2, y0 - w / 2, z0, x1 + w / 2, y1 + w / 2, z1)
    inner = cube(name + "_i", x0 + w / 2, y0 + w / 2, z0 - 1,
                 x1 - w / 2, y1 - w / 2, z1 + 1)
    boolop(outer, inner, 'DIFFERENCE')
    return outer


# ---------------- BASE -------------------------------------------------------
base = cube("base", OX0, OY0, 0, OX1, OY1, BASE_H)
cav = cube("cavity", IX0, IY0, FLOOR, IX1, IY1, BASE_H + 1)
boolop(base, cav, 'DIFFERENCE')

# five M3 bosses (heat-set inserts: bore 4.0, boss OD 8) - H5 is F-18
for hx, hy in HOLES:
    b = cyl("boss", hx, hy, FLOOR, FLOOR + STANDOFF, 4.0)
    boolop(base, b, 'UNION')
    d = cyl("bore", hx, hy, FLOOR + STANDOFF - 6.0, FLOOR + STANDOFF + 0.1, 2.0)
    boolop(base, d, 'DIFFERENCE')

# seal tongue on the wall top, on the seal line
tongue = ring("tongue", SX0, SY0, SX1, SY1, BASE_H - 0.1, BASE_H + TONGUE_H,
              TONGUE_W)
boolop(base, tongue, 'UNION')

# J1 is TOP-ENTRY: harness plugs in from above and leaves through an M16
# IP68 gland in the -X wall; external ring boss gives the gland nut a flat seat
gz = BOARD_TOP + 9.4
gboss = cyl("gland_boss", GLAND_Y, gz, OX0 - 2.0, OX0 + WALL, 12.0, axis='X')
boolop(base, gboss, 'UNION')
gh = cyl("gland_hole", GLAND_Y, gz, OX0 - 3.0, IX0 + 1, GLAND_HOLE_R, axis='X')
boolop(base, gh, 'DIFFERENCE')

# M12 ePTFE vent plug, -Y wall: a sealed box cycling -20..+70 C pumps air
# through the gasket otherwise - pressure equalisation is part of IP67 intent
vz = BOARD_TOP + 11.0
vboss = cyl("vent_boss", VENT_X, vz, OY0 - 1.5, OY0 + WALL, 9.0, axis='Y')
boolop(base, vboss, 'UNION')
vh = cyl("vent_hole", VENT_X, vz, OY0 - 3.0, IY0 + 1, VENT_HOLE_R, axis='Y')
boolop(base, vh, 'DIFFERENCE')

# +X wall: the RF corridor side. SMA positions are the same in both variants
# so one mould with a drill-out change covers both.
sma_z = BOARD_TOP + 6.0
for sy in SMA_YS:
    seat = cyl("sma_seat", sy, sma_z, OX1 - 1.0, OX1 + 1.5, 6.0, axis='X')
    boolop(base, seat, 'UNION')
    if INTERNAL:
        # sealed: 1 mm pilot dimple only (installer's drill option)
        p = cyl("sma_pilot", sy, sma_z, OX1 + 0.5, OX1 + 2.0, 0.5, axis='X')
        boolop(base, p, 'DIFFERENCE')
    else:
        # through hole for the bulkhead jack; the seat face is the O-ring land
        h = cyl("sma_hole", sy, sma_z, OX1 - WALL - 1.5, OX1 + 2.0,
                SMA_HOLE_R, axis='X')
        boolop(base, h, 'DIFFERENCE')
        # 0.4 deep O-ring recess (d9 land) so the jack's O-ring is captive,
        # not just squashed against a flat face
        rec = cyl("sma_oring", sy, sma_z, OX1 + 1.1, OX1 + 2.0, 4.5, axis='X')
        boolop(base, rec, 'DIFFERENCE')

# lid screw posts OUTSIDE the seal line: 4 corners + 2 long-side midpoints
# (90 mm long sides - corners alone leave the gasket under-compressed mid-span)
XM = (OX0 + OX1) / 2
POSTS = [(OX0 - 3.0, OY0 - 3.0), (OX1 + 3.0, OY0 - 3.0),
         (OX0 - 3.0, OY1 + 3.0), (OX1 + 3.0, OY1 + 3.0),
         (XM, OY0 - 3.0), (XM, OY1 + 3.0)]
for px, py in POSTS:
    p = cyl("post", px, py, 0, BASE_H, 4.5)
    boolop(base, p, 'UNION')
    d = cyl("pilot", px, py, BASE_H - 12.0, BASE_H + 0.1, 1.25)
    boolop(base, d, 'DIFFERENCE')

# chassis flanges (MEWP rail, M5 slots) on the +-Y ends
for fy0, fy1 in ((OY0 - 14.0, OY0), (OY1, OY1 + 14.0)):
    f = cube("flange", OX0 + 8, fy0, 0, OX1 - 8, fy1, 4.0)
    boolop(base, f, 'UNION')
    for sx in (OX0 + 20, OX1 - 20):
        s = cube("slot", sx - 3, (fy0 + fy1) / 2 - 5.5, -1,
                 sx + 3, (fy0 + fy1) / 2 + 5.5, 5)
        boolop(base, s, 'DIFFERENCE')

# ---------------- LID --------------------------------------------------------
LZ0 = BASE_H
LTOP = LZ0 + LID_POCKET + LID_PLATE
lid = cube("lid", OX0, OY0, LZ0, OX1, OY1, LTOP)
pocket = cube("lid_pocket", IX0, IY0, LZ0 - 1, IX1, IY1, LZ0 + LID_POCKET)
boolop(lid, pocket, 'DIFFERENCE')
# O-ring cord groove in the lid rim, on the seal line, facing the tongue
groove = ring("groove", SX0, SY0, SX1, SY1, LZ0 - 1, LZ0 + GROOVE_D, GROOVE_W)
boolop(lid, groove, 'DIFFERENCE')

CEIL = LZ0 + LID_POCKET          # lid interior ceiling (antenna mount face)

if INTERNAL:
    # --- LTE FPC bay: 0.4 recess locating the FPC, four d1.6 heat-stake
    # posts for a plastic clamp frame (F-23 mechanical retention, no metal
    # over the antenna), and a strap channel as the second retention path
    fx, fy = FPC_C
    bx0, bx1 = fx - FPC_L / 2 - 0.5, fx + FPC_L / 2 + 0.5
    by0, by1 = fy - FPC_W / 2 - 0.5, fy + FPC_W / 2 + 0.5
    assert bx1 <= IX1 - 1.0 and by0 >= IY0 + 1.0, "FPC bay hits the skirt"
    rec = cube("fpc_recess", bx0, by0, CEIL - 0.4, bx1, by1, CEIL + 0.1)
    boolop(lid, rec, 'DIFFERENCE')
    for sx_ in (bx0 - 1.6, bx1 + 1.6):
        for sy_ in (by0 - 1.6, by1 + 1.6):
            post = cyl("stake", sx_, sy_, CEIL - 2.0, CEIL, 0.8)
            boolop(lid, post, 'UNION')
    for rx in (bx0 - 4.5, bx1 + 2.5):
        assert IX0 + 0.5 <= rx and rx + 2.0 <= IX1 - 0.5, "strap rib in skirt"
        rib = cube("strap_rib", rx, by0 - 3.0, CEIL - 1.6, rx + 2.0,
                   by1 + 3.0, CEIL)
        boolop(lid, rib, 'UNION')

    # --- GNSS patch pocket. The patch is mounted ground-side to the lid
    # ceiling so its radiating face looks up through the 2.5 mm ASA plate,
    # >= 3 mm from every wall. Four corner L-tabs (1.5 thick, 6 mm arms,
    # 0.2 clearance) with a 0.6 retention lip under the ceramic.
    px, py = PATCH_C
    px0, px1 = px - PATCH / 2, px + PATCH / 2
    py0, py1 = py - PATCH / 2, py + PATCH / 2
    assert px1 + WALL_CLR <= IX1 and py1 + WALL_CLR <= IY1 and \
        px0 - WALL_CLR >= IX0 and py0 - WALL_CLR >= IY0, \
        "patch violates the 3 mm wall clearance"
    TH = PATCH_H + 0.2
    for cx_, sx in ((px0, -1), (px1, +1)):
        for cy_, sy in ((py0, -1), (py1, +1)):
            ax = span(cx_, -sx, 0.0, 6.0)        # arm runs INTO the edge
            ay = span(cy_, sy, 0.2, 1.7)         # sits just outside in y
            arm = cube("patch_tab", ax[0], ay[0], CEIL - TH, ax[1], ay[1],
                       CEIL)
            boolop(lid, arm, 'UNION')
            bx = span(cx_, sx, 0.2, 1.7)
            by = span(cy_, -sy, 0.0, 6.0)
            arm = cube("patch_tab", bx[0], by[0], CEIL - TH, bx[1], by[1],
                       CEIL)
            boolop(lid, arm, 'UNION')
            lx = span(cx_, -sx, 0.0, 1.5)        # lip tucks UNDER the corner
            ly = span(cy_, -sy, 0.0, 1.5)
            lip = cube("patch_lip", lx[0], ly[0], CEIL - TH, lx[1], ly[1],
                       CEIL - TH + 0.6)
            boolop(lid, lip, 'UNION')
            # corner block joining lip and both arms
            kx = span(cx_, sx, 0.0, 1.7)
            ky = span(cy_, sy, 0.0, 1.7)
            blk = cube("patch_corner", kx[0], ky[0], CEIL - TH, kx[1], ky[1],
                       CEIL)
            boolop(lid, blk, 'UNION')
    # pigtail clip between the patch and the FPC bay: keeps the 120 mm
    # RG1.13 off the SIM bay below
    clip = cube("pigtail_clip", px1 - 4.0, py0 - 8.0, CEIL - 3.0,
                px1 - 2.0, py0 - 3.0, CEIL)
    boolop(lid, clip, 'UNION')

# lid screw holes into the base posts (countersunk M3 self-tap)
for px, py in POSTS:
    ear = cyl("lid_ear", px, py, LZ0, LTOP, 4.5)
    boolop(lid, ear, 'UNION')
    h = cyl("lid_hole", px, py, LZ0 - 1, LTOP + 1, 1.7)
    boolop(lid, h, 'DIFFERENCE')
    cs = cyl("lid_csink", px, py, LTOP - 1.6, LTOP + 0.1, 3.2)
    boolop(lid, cs, 'DIFFERENCE')

# ---------------- reference parts (not exported, shown in renders) -----------
ref, lid_parts = [], []
if INTERNAL:
    fx, fy = FPC_C
    fpc = cube("REF_lte_fpc", fx - FPC_L / 2, fy - FPC_W / 2,
               CEIL - 0.4 - FPC_T, fx + FPC_L / 2, fy + FPC_W / 2, CEIL - 0.4)
    px, py = PATCH_C
    patch = cube("REF_gnss_patch", px - PATCH / 2, py - PATCH / 2,
                 CEIL - PATCH_H, px + PATCH / 2, py + PATCH / 2, CEIL)
    lid_parts = [fpc, patch]
    ref += lid_parts
else:
    for sy in SMA_YS:
        jack = cyl("REF_sma_jack", sy, sma_z, OX1 - WALL - 6.0, OX1 + 9.0,
                   3.1, axis='X')
        nut = cyl("REF_sma_nut", sy, sma_z, OX1 + 1.5, OX1 + 4.0, 4.6,
                  axis='X')
        ref += [jack, nut]
gland = cyl("REF_gland", GLAND_Y, gz, OX0 - 22.0, OX0 - 2.0, 9.5, axis='X')
vent = cyl("REF_vent", VENT_X, vz, OY0 - 6.0, OY0 - 1.5, 7.0, axis='Y')
board = cube("REF_board", 0, 0, FLOOR + STANDOFF, BW, BH, BOARD_TOP)
ref += [gland, vent, board]


# ---------------- material / export / render ---------------------------------
def mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1.0)
    return m


m_body = mat("asa_light_grey", (0.86, 0.86, 0.83))     # product spec
m_pcb = mat("pcb_green", (0.10, 0.35, 0.18))
m_ant = mat("antenna_amber", (0.85, 0.55, 0.15))
m_cer = mat("ceramic_white", (0.95, 0.95, 0.92))
m_metal = mat("nickel", (0.55, 0.57, 0.60))
for o in (base, lid):
    o.data.materials.append(m_body)
for o in ref:
    n = o.name
    o.data.materials.append(m_pcb if "board" in n else
                            m_cer if "patch" in n else
                            m_ant if "fpc" in n else m_metal)

for o, nm in ((base, "base"), (lid, "lid")):
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.wm.stl_export(filepath=os.path.join(OUT, nm + ".stl"),
                          export_selected_objects=True)

scene.render.engine = 'BLENDER_WORKBENCH'
sh = scene.display.shading
sh.light = 'STUDIO'
sh.color_type = 'MATERIAL'
sh.show_cavity = True
sh.show_shadows = True
sh.background_type = 'VIEWPORT'
sh.background_color = (0.93, 0.93, 0.93)
scene.render.resolution_x, scene.render.resolution_y = 1400, 1000
cam = bpy.data.cameras.new("cam")
camo = bpy.data.objects.new("cam", cam)
scene.collection.objects.link(camo)
scene.camera = camo


def look_at(o, target):
    from mathutils import Vector
    d = Vector(target) - o.location
    o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def shot(name, pos, target, lens=50):
    cam.lens = lens
    camo.location = pos
    look_at(camo, target)
    scene.render.filepath = os.path.join(OUT, f"housing-{name}.png")
    bpy.ops.render.render(write_still=True)


cx, cy = (OX0 + OX1) / 2, (OY0 + OY1) / 2
# 1) closed assembly, iso
shot("closed", (cx + 170, cy - 150, 130), (cx, cy, BASE_H / 2))
# 2) +X wall (SMA side) straight on
shot("sma-wall", (cx + 260, cy, BASE_H * 0.6), (OX1, cy, BASE_H * 0.55))
# 3) exploded: lid lifted 35, lid-mounted antennas travel with it
for o in [lid] + lid_parts:
    o.location.z += 35.0
shot("exploded", (cx + 190, cy - 170, 150), (cx, cy, BASE_H * 0.8))
# 4) lid interior: hide the base, look straight up at the lifted lid's inside
hidden = [base] + [r for r in ref if r not in lid_parts]
for o in hidden:
    o.hide_render = True
shot("lid-inside", (cx, cy - 0.01, LZ0 + 35.0 - 150.0), (cx, cy, LZ0 + 35.0),
     lens=55)
for o in hidden:
    o.hide_render = False
for o in [lid] + lid_parts:
    o.location.z -= 35.0

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "housing.blend"))
print(f"HOUSING_DONE variant={VARIANT} lid_pocket={LID_POCKET} "
      f"base={OX1-OX0:.0f}x{OY1-OY0:.0f}x{BASE_H:.1f} "
      f"lid_h={LTOP-LZ0:.1f}")
