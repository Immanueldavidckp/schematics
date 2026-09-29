MEWP TELEMATICS TRACKER - MANUFACTURING PACKAGE
================================================
Revision 53dae68 (git branch relief6-stretch), generated 2026-09-29.
Board 100.0 x 68.0 mm, 4 layers, 1.6 mm, ENIG.
Checks passed before this package was made: DRC 0 errors / 0 unconnected,
ERC 0 errors, MCU pin map 47/47, 0 duplicate items, 0 overlapping holes,
BOM verified line by line against LCSC/JLCPCB (0 open), part heights
checked against the enclosure.

WHAT TO SEND TO WHOM
--------------------
1. PCB fabricator (bare boards)
     1_PCB_fabrication/gerbers.zip          <- the board itself (all layers + drill)
     1_PCB_fabrication/fabrication-drawing.pdf
     1_PCB_fabrication/telematics-tracker.ipc   (electrical test netlist, IPC-D-356)
     1_PCB_fabrication/telematics-tracker-odb.zip (the same board as ODB++, if they prefer)
2. Assembler (PCBA)
     JLCPCB:            gerbers.zip, then 2_PCB_assembly/bom-jlcpcb.csv and pick-and-place.csv
     local assembler:   2_PCB_assembly/bom-with-manufacturer-part-numbers.csv (manufacturer +
                        MPN on every line), pick-and-place.csv, assembly-top.pdf, assembly-bottom.pdf
3. Enclosure maker / 3D printing
     4_enclosure/  (see housing-notes.md; STL for printing, STEP for the lids, Blender source)

PCB FABRICATION SPECIFICATION
-----------------------------
Layer count ........ 4
Layer order ........ 1 F.Cu (top)       telematics-tracker-F_Cu.gtl
                     2 GND_L2 (inner 1) telematics-tracker-GND_L2.g1
                     3 PWR_L3 (inner 2) telematics-tracker-PWR_L3.g2
                     4 B.Cu (bottom)    telematics-tracker-B_Cu.gbl
Outline ............ telematics-tracker-Edge_Cuts.gm1: 100.0 x 68.0 mm, R2.0 corners
Thickness .......... 1.6 mm +/-10 %
Stackup ............ JLC04161H-7628 or equivalent:
                     L1-L2 7628 prepreg 0.2104 mm (er 4.4) / core 1.065 mm (er 4.6) /
                     L3-L4 7628 prepreg 0.2104 mm. The GNSS antenna feed depends on it.
Copper ............. 1 oz outer, 0.5 oz inner (finished)
Material ........... FR-4, Tg >= 150 preferred (sealed box, 70 C ambient)
Surface finish ..... ENIG (flat pads for the LGA-144 modem and the 0.5 mm-pitch MCU)
Solder mask ........ both sides (green, or any colour)
Silkscreen ......... both sides, white
Min track/space .... 0.127 / 0.127 mm (5 mil)
Min via ............ 0.45 mm pad, 0.20 mm drill; smallest hole 0.20 mm
Drill sizes ........ plated: 0.20 mm x323, 0.30 mm x146, 0.40 mm x32, 0.95 mm x3, 1.02 mm x12, 3.20 mm x5
                     NON-plated: 0.80 mm x2, 1.10 mm x2
                     (connector / SIM-holder locating pegs; marked NPTH in the drill file)
Vias ............... tented both sides. One via is in a pad (U2 pin 47, ground): plugged /
                     epoxy filled and capped if offered, otherwise acceptable as is.
Impedance control .. YES: 50 ohm coplanar waveguide on layer 1 (GNSS antenna feed):
                     track 0.40 mm, gap 0.30 mm to layer-1 ground, reference plane layer 2.
                     Valid for the stackup above - if your standard stackup differs, send it
                     to us before building so the track can be re-sized.
Quality / test ..... IPC-6012 Class 2, 100 % electrical test (telematics-tracker.ipc)
Panelisation ....... fab's choice; keep 5 mm rails and fiducials if the boards are assembled

IMPORTANT: a local fab must be able to do 0.127 mm track/space and 0.20 mm drills on
4 layers. If they cannot, do not let them "adjust" the files - tell us.

ASSEMBLY
--------
Placement .......... double-sided SMT: 137 parts on top, 53 on the bottom
                     (190 placements in pick-and-place.csv); through-hole: J1, J2
BOM ................ 76 lines, 184 parts; DNP parts are excluded from BOM and placement
Rotation ........... check U1 (EC200U), U2 (LQFP-48) and U6 (QFN-24) in the placement preview
Test points ........ TPx are bare pads (not purchased parts)
CONFORMAL COATING .. MANDATORY on every board, prototypes included (safety: 100 V creepage
                     at U5). Coat both sides after assembly and before any 100 V test.
                     Keep coating OFF: J1, J2, AF1, AF2 (U.FL), X1 (SIM holder), test points.

ENCLOSURE (IP65)
----------------
Two variants (4_enclosure/internal-antennas, external-antennas): base 112 x 76 x 31.1 mm,
ASA light grey, O-ring cord seal, 6 lid screws outside the seal, M16 IP68 cable gland,
M12 ePTFE vent. Drawn to IP67 intent so IP65 has margin; jet-test a prototype.
Concept status: good for 3D-printed prototypes and quotes; a moulded version needs a CAD
redraw with draft angles (housing-notes.md, open items).

FILE INDEX
----------
  1_PCB_fabrication/fabrication-drawing.pdf
  1_PCB_fabrication/gerbers.zip
  1_PCB_fabrication/telematics-tracker-odb.zip
  1_PCB_fabrication/telematics-tracker.ipc
  1_PCB_fabrication/gerbers/telematics-tracker-B_Cu.gbl
  1_PCB_fabrication/gerbers/telematics-tracker-B_Mask.gbs
  1_PCB_fabrication/gerbers/telematics-tracker-B_Paste.gbp
  1_PCB_fabrication/gerbers/telematics-tracker-B_Silkscreen.gbo
  1_PCB_fabrication/gerbers/telematics-tracker-Edge_Cuts.gm1
  1_PCB_fabrication/gerbers/telematics-tracker-F_Cu.gtl
  1_PCB_fabrication/gerbers/telematics-tracker-F_Mask.gts
  1_PCB_fabrication/gerbers/telematics-tracker-F_Paste.gtp
  1_PCB_fabrication/gerbers/telematics-tracker-F_Silkscreen.gto
  1_PCB_fabrication/gerbers/telematics-tracker-GND_L2.g1
  1_PCB_fabrication/gerbers/telematics-tracker-PWR_L3.g2
  1_PCB_fabrication/gerbers/telematics-tracker-drl_map.gbr
  1_PCB_fabrication/gerbers/telematics-tracker-job.gbrjob
  1_PCB_fabrication/gerbers/telematics-tracker.drl
  2_PCB_assembly/assembly-bottom.pdf
  2_PCB_assembly/assembly-top.pdf
  2_PCB_assembly/board-bottom.png
  2_PCB_assembly/board-top.png
  2_PCB_assembly/bom-jlcpcb.csv
  2_PCB_assembly/bom-with-manufacturer-part-numbers.csv
  2_PCB_assembly/pick-and-place.csv
  3_documentation/assembled-board.step
  3_documentation/bom-audit.md
  3_documentation/schematic.pdf
  4_enclosure/housing-notes.md
  4_enclosure/external-antennas/base.stl
  4_enclosure/external-antennas/housing-base-inside.jpg
  4_enclosure/external-antennas/housing-closed.jpg
  4_enclosure/external-antennas/housing-exploded.jpg
  4_enclosure/external-antennas/housing-lid-inside.jpg
  4_enclosure/external-antennas/housing-sma-wall.jpg
  4_enclosure/external-antennas/housing.blend
  4_enclosure/external-antennas/lid.step
  4_enclosure/external-antennas/lid.stl
  4_enclosure/internal-antennas/base.stl
  4_enclosure/internal-antennas/housing-base-inside.jpg
  4_enclosure/internal-antennas/housing-closed.jpg
  4_enclosure/internal-antennas/housing-exploded.jpg
  4_enclosure/internal-antennas/housing-lid-inside.jpg
  4_enclosure/internal-antennas/housing-sma-wall.jpg
  4_enclosure/internal-antennas/housing.blend
  4_enclosure/internal-antennas/lid.step
  4_enclosure/internal-antennas/lid.stl

(This file and everything listed is in telematics-tracker-mfg-2026-09-29-53dae68.zip.)
