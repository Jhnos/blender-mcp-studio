# V6 — biaxial roots and two pin workflows

## Visual target

Inspect actual generated images only. Do not infer dimensions, strength, mobility or
print success from pictures. A fresh reviewer must report each item separately.

| ID | Observable target | Image |
|---|---|---|
| A | Side view shows roots widening gradually from each ear toward the disc | biaxial_side |
| B | Detail shows sloping roots in both principal directions | biaxial_detail |
| C | One pin has enlarged stops at both ends | pin_styles, left |
| D | Another pin has a visible groove and a separate open C clip | pin_styles, right |
| E | Separate print layout contains two bodies, two pins and two clips | biaxial_detail |
| F | PIP preview contains one paired joint in complementary top-front and bottom-back orientations; pin_styles independently exposes both captive-pin heads | print_in_place, pin_styles |
| G | Top view has an open centre, four holes and no protruding roots | biaxial_top |
| H | Parts and captions are framed and legible | all above |
| I | Separate assembly plus an isolated installed-coordinate view exposes two grooved pins and two C clips | separate_assembled |

## Manufacturing boundaries

- All exported STL coordinates are millimetres. Use 100% mm in a slicer; use import scale
  0.001 in a metre-based Blender scene, or open the `.blend`.
- `print_in_place_2body_double_head_mm.stl` contains two interleaved bodies and two captive
  pins in their assembled positions. Do **not** auto-arrange its individual shells.
  Axis is vertical in this coupon. Radial shaft clearance is 0.25 mm; recessed stop-head
  clearance is 0.3 mm radially and axially. Release, bridging and support strategy are untested.
- `separate_parts_2body_2pin_2clip_mm.stl` contains six laid-out parts. The C clip seats
  laterally in the pin groove inside the male-ear recess. It is only 0.9 mm thick and is
  an experimental printed retainer, not a rated spring or safety clip.
- The same body is used by both workflows. Body STL, grooved-pin STL and clip STL are also
  exported separately. Double-headed pins are intentionally not offered as insertable parts.
- Positive geometric stops do not establish reliable retention force. Do not load or drive
  the chain until the physical coupon proves mobility and retention without fracture.
- Side ramps rise from the disc surface at Z=2 mm to the shoulder at Z=4.4 mm, meeting
  the circular ear's lower region. Ear mating faces above the shoulder remain parallel for
  rotation; this is a biaxial root reinforcement, not a fully tapered bearing face.
- Body OD is 36 mm, pitch 19 mm, complete body height 29.6 mm; centre Ø10 mm and four
  Ø2.4 mm tendon holes remain. Ear OD 10.6 mm leaves 2 mm around the Ø6.6 mm retainer seat.

## Repeatable checks

Run the generic artifact checker with `biaxial_hinge.json`, then with
`biaxial_hinge_pip.json --skip-generate` and `biaxial_hinge_split.json --skip-generate`.
Run the generic mesh-probe checker with `biaxial_hinge_probe.json` and
`biaxial_hinge_split_probe.json`. Never run these concurrently with real CI or scene edits.
The pin/body tests are static; sampled body sweeps are not continuous collision certification.

## Independent visual result — final round

| ID | Result | Direct observation |
|---|---|---|
| A | PASS | Side/detail roots broaden from each narrow ear base to a wider disc footprint. |
| B | PASS | Detail plus side/top views expose sloped root faces in two perpendicular directions. |
| C | PASS | Captive pin has enlarged circular stops at both shaft ends. |
| D | PASS | Removable pin has a visible neck groove; separate clip is visibly open and C-shaped. |
| E | PASS | Detail contains exactly two bodies, two cyan pins and two red clips, all uncropped. |
| F | PASS | PIP top-front and bottom-back views are visually distinct; pin close-up exposes both heads. |
| G | PASS | Full disc, open centre, four tendon holes and contained root footprints are visible. |
| H | PASS | All required geometry and titles are legible and uncropped across six final PNGs. |
| I | PASS | Separate view shows the full assembly plus two pins/two clips at installed relative positions. |

The reviewer inferred no exact coordinate, fit, strength, mobility or print-performance claim
from the PNGs. Those remain owned by numeric probes or the physical coupon.
