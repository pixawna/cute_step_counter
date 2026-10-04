STEP COUNTER V1 - CAD AND PRINT KIT
Units: millimetres. Revision: 04 October 2026.

WHAT IS INCLUDED
cad/step_counter.scad: native OpenSCAD solid model. Open to inspect the assembly.
cad/parameters.json + cad/generate_model.py: editable parametric master source.
stl/: 12 individual printable parts, pre-oriented with their lowest point at Z=0.
fit-check/: 3 low-material test pieces. Print these first.
cad/assembly/: parts at assembled coordinates, for inspecting the assembly.
cad/assembly_for_visualization_NOT_FOR_PRINT.stl: assembled mesh, not a print job.
cad/hardware_reference_NOT_FOR_PRINT/: assumed electronic component envelopes.
renders/: views generated from the actual exported enclosure meshes.
reference/: approved appearance concept and planning drawing.
cad/validation.json + export-verification.json: digital geometry check results.

This is a printable fit-check prototype of the approved design, not a physically
tested final electronics assembly. It follows the Mona Robo delivery structure.
OpenSCAD source is included; no STEP or FreeCAD B-rep file is included.

SIZE AND APPEARANCE
70 wide x 78 high x 28 deep, 88 high including the loop.
The 28 mm envelope includes shallow front accent pieces; the cream shell front
face sits 1.2 mm behind their outermost point. The nominal covers/walls are 2 mm.
Front corners R 24; edges have a small printable bevel instead of a domed surface.
Screen opening 30 x 37, corner R 1; centered until the real display is measured.
Loop OD 12, hole ID 6, thickness 6; integrated into the lavender structural shell.
Cream front/back; lavender middle shell, feet and cheeks. Eyes and mouth are
engraved for dark paint. The rear cheeks are also engraved for paint.
Render images omit electronics: the opening is empty, revealing the carrier.

PRINTABLE PARTS (ONE EACH)
01_front_bezel: face, screen opening, board edge seats and structural posts.
02_middle_shell: perimeter ring and reinforced lanyard loop.
03_back_cover: removable cover and four recessed screw holes.
04_sensor_carrier: removable plate with central underside relief.
05_tft_retainer_left / right: slotted display PCB edge clamps.
06_sensor_clamp_left / right: slotted sensor PCB edge clamps.
07_foot_left / right: shallow decorative inserts.
08_cheek_left / right: decorative circular inserts.

COMPONENT BASIS AND UNVERIFIED ASSUMPTIONS
Selected TFT: https://robocraze.com/products/1-8-inch-tft-lcd-module
Seller PCB specification: 62 x 38; mounted portrait, 38 wide x 62 high.
Selected sensor: https://robocraze.com/products/adxl-345
Seller envelope: 30 x 20 x 10. The 30 x 20 size is provisionally treated as
the PCB outline; the seller has not supplied a dimensioned mechanical drawing.

No manufacturer hole pattern is guessed: the design uses adjustable edge clamps.
The following are explicit assumptions, adjustable in cad/parameters.json:
TFT PCB thickness 1.6; PCB front atZ 7.6; LCD frame 34 x 46, front atZ 3.6.
TFT rear components fit 30 x 42, end atZ 11.3; header zone 38 x 7 at top of PCB.
Sensor PCB thickness 1.6, front atZ 14.8; total module height 10, ends atZ 24.8.
Sensor components fit 26 x 16, leaving clear edge-clamping margins.
These envelopes may differ from the actual board revision and connector style.
Tall straight pin headers or Dupont plugs may require a deeper case.

The sensor carrier begins atZ 12.3, giving 1 mm from the assumed TFT rear limit.
The sensor underside has 0.5 mm clearance above the carrier surface and a 28 x 18
central relief. Check solder tails and traces before tightening either board.
The rear interior isZ 26: nominal sensor rear clearance 1.2 mm.
Retainers touch only the assumed clear PCB edge margins. They must not bear on
LCD glass, headers or components. Do not force a mismatching board into the case.
MCU, battery, switch and charging circuit are unspecified and are not fitted.
There is no USB/power opening yet. These choices may require a deeper case.

FIT CHECKS
01_window_alignment.stl: thin front-face slice. Compare screen opening/offset.
02_tft_outline_gauge.stl: 39 x 63 opening;0.5 mm allowance per side around PCB.
03_fastener_test.stl: orient long side horizontally. From left to right:
blind pilot diameters 1.5,1.6,1.7; then 2.3 through-hole with 4.3 head recess.
Use the default 1.6 pilot with a suitable M2 tap. Test actual printed fit first.
Mating lips have 0.3 mm clearance per side. Check a trial shell before final use.

FASTENERS AND OTHER ITEMS
4 x M2 x 10 pan-head machine screws for rear closure (nominal 7.2 mm engagement).
4 x M2 x 5 for TFT retainers (nominal 3.4 mm engagement).
2 x M2 x 6 for sensor carrier (nominal 4 mm engagement).
2 x M2 x 5 for sensor clamps (nominal 3.4 mm engagement).
The screw length is measured from underneath the head. Geometry is checked for
heads up to 3.8 mm diameter x 1.6 mm tall; the rear recess is 4.3 mm diameter.
Tap blind 1.6 mm pilots M2 after printing. Clear swarf before adding electronics.
No heat-set inserts are modelled. Use a light hand: plastic threads can strip.
Confirm engagement and pilot depth; washers change the effective engagement.
Small amount of plastic-compatible adhesive for foot/cheek inserts; dark paint
for engraved features. Add thin electrical insulation where the real boards need
it, and account for any added thickness in the seating parameters.

ASSEMBLY ORDER
1. Print the coupons, check the purchased boards, and adjust parameters if needed.
2. Print/clean the enclosure; tap pilot holes with electronics absent.
3. With front shell face down, lay TFT on its four PCB edge seats. Check viewing
   alignment. Fit left/right retainers with fourM2 x 5 screws; tighten gently.
4. Route low-profile display wires, then slide the middle shell over the front
   registration lip. Keep wires clear of cover posts and the screen.
5. Fit the ADXL 345 on the carrier corner lands, electronics facing the rear.
   Secure with the two sensor clamps andM2 x 5 screws. Verify underside clearance.
6. Screw the carrier onto its two posts usingM2 x 6. Wire the sensor to the chosen
   controller. Sensor is rigidly supported; do not leave it free inside the case.
7. Check all wire bends and connector clearances. Fit the rear cover registration
   lip and close with fourM2 x 10 screws. Stop if the lid does not seat freely.
8. Glue the decorative inserts into their matching front recesses and paint faces.

PRINTING START POINT
0.4 mm nozzle,0.2 mm layers,4 walls; PLA for initial fit, PETG optional for use.
Use the individual STLs, not the assembled model. Import units as millimetres.
The main shell prints with its front seam/loop plane on the bed; its loop is
integrated with no separate floating island. Covers print exterior face down.
Retainers, carrier and accents have flat print bases. Review small overhangs,
engraving, and screw recess bridges in the slicer; use local supports only where
needed. A brim may help the tall front posts. Avoid supports on mating surfaces.
Check bed adhesion for 0.8 mm cheek inserts. Paint or use separate filament colours.
The full CAD print_layout exceeds common small beds; slice parts individually.

EDITING AND REGENERATION
Open cad/step_counter.scad in OpenSCAD. The variable part selects 'assembly',
'print_layout', an exact STLstem (e.g. '01_front_bezel'), or a coupon selector
(e.g. 'coupon_02_tft_outline_gauge'). The .scad contains native CSG solids, not
external mesh imports. It can be edited, rendered and exported in OpenSCAD.
For dimension changes, edit cad/parameters.json and regenerate using Python:
  python -m pip install -r cad/requirements.txt
  python cad/generate_model.py
  python cad/verify_print_kit.py
  python cad/render_model.py
Python/JSON are the parametric master; regeneration replaces generated SCAD/STLs.
Some carrier/clip dimensions are in generate_model.py. If changing PCB size,
update these as well as the associated envelope/retention parameters.

VALIDATION AND LIMITS
Each saved print STL and coupon is checked for a single connected closed surface,
consistent winding, finite coordinates, positive volume and placement atZ 0.
Saved assembly meshes are checked for part/part and assumed electronics collisions.
Representative screw heads are also checked against the enclosure and hardware.
The assembled envelope is checked against 70 x 88 x 28. Tolerance for overlap checks
is 0.01 cubic mm. These checks do not prove physical fit, thread strength, printer
tolerances, lanyard load capacity, waterproofing or functional step counting.
Native OpenSCAD text is generated from the same CSG operations as the meshes;
the delivered geometry was evaluated in manifold3d, not separately in OpenSCAD.
The accelerometer and screen need a controller running step-count firmware and
power. The concept reference's direct sensor-to-display wiring is not a circuit.
