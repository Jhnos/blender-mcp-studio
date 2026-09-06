# Octopus hand V1 — target, evidence and manufacturing limits

Five V6 biaxial arms on a pentagonal palm, printed in one piece with the cables threaded
afterwards. Read [generated-artifacts.md](generated-artifacts.md) for the workflow and
[biaxial-hinge-v6.md](biaxial-hinge-v6.md) for the arm's own dimensional contract — this
document only covers what the hand adds.

## What it is

| | |
|---|---|
| Palm | Regular pentagon, 6 mm thick, 151.8 mm across corners |
| Arms | Five, each 5 bodies on a Ø36 mm V6 profile, 19 mm pitch, stations at radius 41.5 mm |
| Joints | Five per arm — four between bodies plus one where the palm socket carries the first body |
| Cables | Four Ø2.4 mm tendon holes per arm, 20 in total, at radius 13 mm about each arm axis |
| Wiring | One Ø10 mm channel on the palm axis, clear of every tendon hole |
| Grip pads | Four per repeated body, on the plain diagonals, Ø42 across their flat faces |
| Tip | Terminal hexagonal cap, Ø42 shoulder tapering to Ø22, two cross-bores anchoring four cables |
| Whole hand | 144.408 × 138.545 × 117.000 mm, 129 860 triangles, **76 separate shells** — palm, 25 bodies, 50 captive pins. Do **not** auto-arrange them |

The palm's top face is treated as a body centre plane. That is the whole trick: the socket
carries the same male ears any body carries on its +Z face, so V6's `create_body` is reused
without modification and the arm gains a base joint for free.

## Joint axes

A hinge turns about its pin axis, so where the pin points decides what the joint can do.

| Joint | Pin axis | The arm can |
|---|---|---|
| 0 — palm socket | tangential, across the radius | swing **in toward the palm centre and back out** |
| 1 — body 1↔2 | radial, along the radius | swing sideways around the palm |
| 2, 4 | tangential | in and out |
| 3 | radial | sideways |

The base joint being radial-swinging is the point of the whole hand: it is the joint that
closes the grip. `palm_socket_twist_deg` turns the socket a quarter turn off its arm's radial
heading to get it, and every body above is twisted to match so the ears still meet.

Measured in the live scene, not derived: each arm's base pin axis sits **90.0°** to its own
radius at all five stations (0°/90°, 72°/162°, 144°/54°, 216°/126°, 288°/18°).

## Gripping surfaces

The repeated bodies carry four pads each, on the diagonals. That is the only rim free
of joint hardware — ears take the cardinal directions — and it is also the choice that
survives the chain's twist, since a diagonal maps onto a diagonal under ninety degrees.
Each pad's outer face is flat, because a flat face beds against an object where a
cylinder only touches it on a line, and its underside is chamfered at 45° so it is not
a bare overhang when printed upright.

The tip is a terminal segment, not a body with parts glued on: everything above the
disc is cut away, unused ears included, and replaced by a six-faced cap. Cables are
anchored by two through-bores that each cross one opposed pair of tendon holes inside
the cap, so a cable comes up its hole, turns once, and knots through a closed ring.

**The number that bit:** Ø42 is where the pad's *flat face* sits. A flat face is a
chord, and its corners stand further out — 23.17 mm, an envelope of Ø46.35. Spacing the
arms on the face radius let neighbouring pads intersect at the corners while every
per-arm check stayed green. `grip_envelope_radius_mm` is now what the spacing invariant
measures.

## Fit coupon

`test_coupon_mm.stl` — 47.846 × 48.000 × 56.800 mm, 11 636 triangles, 7 shells: a Ø48 mm
chunk of palm carrying two bodies and four captive pins. It is cut from the real geometry,
not modelled again, so what it proves transfers.

It exists because the upright pose's one open question — horizontal pin bores printing as
bridges, and captive pins with an unsupported crown — costs a night to answer on the whole
hand and an hour on this. It carries a base joint (tangential pin), a body-to-body joint
(radial pin) and a grip pad, so both pin headings and the pad's 45° chamfer are in it.

## Print pose

Arms **upright**, palm flat on the bed. Splayed flat the hand does not fit a 220 mm bed;
upright it needs 151.8 mm square by the spec's bound. `OctopusHandSpec` rejects any variant whose upright
envelope exceeds `max_bed_mm`, so the bed is a machine-checked invariant, not a note.

Upright also puts V6's three-stage roots (36.6° / 35.8° / 35.8°, all under 45°) back in the
orientation they were designed for, and keeps the claw's 40° lean self-supporting.

**The open question this pose creates:** the pin axes become horizontal, so the Ø4.5 mm
bores print as bridges and the captive pins have an unsupported crown. That is the opposite
of the orientation `biaxial-hinge-v6.md` recommends for the PIP coupon. Nothing in software
can answer it — it is the first thing the physical print must settle.

## Machine evidence (2026-09-06, real Blender)

Two contracts, both green with no skips:
`scripts/verify/contracts/octopus_hand.json` and `octopus_hand_tips.json`.

| Claim | Evidence |
|---|---|
| Arm chain twists correctly | rotations `(0, 90, 0, 90)` on arm 1; tips `(0, 72, 144, 216, 288)` |
| Grip pads clear the neighbours | inter-arm group of 20, 19 adjacent pairs, all 0 after the stations moved to 41.5 mm |
| One-piece export is complete | 76 shells, matching `printed_part_count` — palm + 25 bodies + 50 pins |
| Cable path open through the cap | tip centre ray misses — it did **not** before the drill was sized off the cap |
| Bodies share one mesh | `shared_mesh_count = 1` for both the 20 plain bodies and the 5 tips |
| No collision inside an arm | 5 per-arm groups, 4 objects each, all adjacent overlaps 0 |
| **No collision between arms** | `HH_OCT_SEG_` group of 20 sorted level-by-level: 19 adjacent pairs, all 0 |
| Tips clear each other | `HH_OCT_TIP_` group of 5, 4 adjacent pairs, all 0 |
| Joint articulates | sweep −34°…+34°, 15 samples, 0 overlap, on the plain body |
| Base joint is radial | live-scene measurement: base pin axis 90.0° to the radius at all five stations |
| Tip clears the joint below it | features start 1.0 mm above the body centre; the ear beneath tops out at −4.2 mm |
| Wire channel open | palm centre ray misses (`center_ray_hit = false`) |
| Cable path open through the tip | tip centre ray misses after the eyelet bosses were unioned on |
| Tip features really applied | `arm_tip_mm.stl` 5140 triangles against the plain body's 3436 |
| Readiness complete | `status = review`, no forbidden structural code, **not truncated** |

Independent STL readback (no Blender): palm 10 220 triangles at 144.408 × 137.340 × 18.800 mm;
arm body 3382 at 43.547 × 43.547 × 29.600 mm; tip 3480 at 43.547 × 43.547 × 32.800 mm;
whole hand 95 260 at 144.408 × 138.545 × 117.000 mm.

## Fresh-context visual rubric

Judge these against the generated PNGs, not against this text.

**Eight views, and why there are eight.** The first review ran on the four overview
shots and returned six of eleven items UNCLEAR — not because anything was wrong, but
because at that distance you cannot count four tendon holes per station, tell which way
a joint axis runs, or separate a 2 mm gap between arms from contact. Four close-ups were
added, each framed on one of those questions: `octopus_palm_bare.png` (holes and centre
channel, arms hidden), `octopus_socket_detail.png` (root profile and the base joint pin),
`octopus_arm_side.png` (down the radius, so a tangential pin reads as one centred disc
and a radial one as two side-by-side), `octopus_tip_top.png` (both cross-bores, no ears).

A rubric is only as good as the evidence it is judged on. Overview renders make a model
look right; they do not let anyone check it.

- **A** Palm is a regular pentagon with an arm station at each of the five vertices.
- **B** Every station shows the three-stage sloped root fused into the palm, not floating on it.
- **C** Twenty tendon holes are visible, four grouped about each arm axis at equal radius.
- **D** One central channel is open through the palm and clear of every tendon hole.
- **E** Each arm shows five bodies with alternating joint axes up its length.
- **F** A captive pin is seated at every joint, including the base joint at the palm.
- **G** Each tip is a six-faced cap with no leftover ears, and its centre channel is open
  through the top face.
- **H** Two cross-bores are visible on the cap, each meeting a pair of tendon holes.
- **K** Every repeated body carries four flat pads on its diagonals, none on an ear.
- **L** The tip's cable paths come out of its underside, not just its top face.
- **I** ~~No arm touches its neighbour anywhere along its length.~~ **Withdrawn from the
  visual rubric.** Two reviewers in a row could not call it, and they were right not to:
  a shaded isometric cannot separate projected overlap from contact, least of all at the
  pad corners. The `HH_OCT_SEG_` collision group measures it directly — twenty bodies
  sorted level by level, nineteen adjacent pairs, zero overlap. An eye is the wrong
  instrument here, and a rubric item nobody can answer is not a gate.
- **J** The print layout view shows three distinct parts: palm, plain body, tip.

## Evidence boundaries

- No physical print, slicer support decision, dimensional-fit, release, grip-force,
  retention, cable-tension or fatigue test has been performed. Every dimension here is a
  fit-coupon dimension; nothing is a rated mechanical claim.
- The claw is an experimental hook. It is not a rated gripper, and the 0.9 mm-class printed
  features inherited from V6 are not rated retainers.
- Readiness reports 92 thin-wall and 4603 overhang sampled faces as warnings across the three
  parts. Those are for slicer and physical review; the check does not certify strength or a
  support strategy.
- Collision testing is discrete surface overlap in the neutral pose plus a single-joint sweep.
  It is not continuous collision detection, and it does not cover the fully curled hand.
- The inter-arm group's adjacency pairs cover arms 1↔2, 2↔3, 3↔4 and 4↔5 at each level. The
  5↔1 pair is not compared directly; the arms are identical on a regular pentagon, so it is
  covered by symmetry rather than by measurement.
- The palm↔first-body joint is not in any adjacency group. Its clearance is inferred from the
  same joint geometry the sweep exercises, not measured in place.
- The tip has **no sweep of its own**. Sweeping it against a copy of itself measured a joint
  the hand does not have — nothing mates above a tip — and that test passed for a reason
  unrelated to the design before the joint axes changed, then failed for one just as
  unrelated after. The joint a tip really hangs from is the one below it, and what stands in
  for a sweep there is the spec invariant that every tip feature stays above the body's
  mid-plane, clear of the ears underneath.
- The pads and the cap add contact **area**; nothing here measures contact **force**, friction
  or whether an object of any given shape is actually held.
- STL carries no unit metadata. Keep mm and 100% in the slicer; import at scale 0.001 into a
  metre-based Blender scene, or open the `.blend`.
