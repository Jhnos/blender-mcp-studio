# Four-DOF alternating-axis tendon hinge chain

**Status:** ACTIVE

## Goal

Create one parametric, repeatable phalanx link that is strong enough for an FDM prototype
and maps cleanly to machined metal. Five identical links must form four serviceable revolute
joints and four continuous tendon routes without a unique printed connector part.

## Context to read

1. `AGENTS.md`
2. `.agents/skills/blender-mcp-studio/SKILL.md`
3. This task only; V1/V2 geometry is preserved in git history, not active design input.

## Specification

- Every link has one distal X-axis male tongue and one proximal Y-axis female clevis.
- Rotate alternate links 90 degrees around the chain axis. The four joint axes must then be
  `J1_X`, `J2_Y`, `J3_X`, and `J4_Y`.
- Use a 4 mm pin interface and concentric 8.1 mm seats for optional MR84 4x8x3 bearings.
  Pins and bearings are standard hardware, not additional printable part types.
- Four tendon holes use a quarter-turn-invariant cross pattern so all five rotated links
  retain the same four straight neutral-position routes.
- Generate a complete assembly view and three-view print layout in millimetres with
  deterministic component names. Keep the former ball-socket version out of this slice.
- This is a concept prototype, not a load-certified actuator. Record fit, fatigue, tendon
  wear, and support assumptions visibly.

## Acceptance checks

- Pure validation tests reject weak lug walls, undersized pins, bad fork clearance, invalid
  bearing seats, non-phalanx proportions, and broken tendon edge walls.
- Blender contains five same-mesh phalanx objects at 0/90/0/90/0 degrees, four named pins,
  eight bearing objects, and four continuous tendon guides.
- Renders make the male tongue, female clevis, X/Y pin alternation, and standard hardware
  legible without cropping.
- Actual MCP print-readiness identifies remaining review items without hiding them.
- Human acceptance and a physical pin/bearing coupon are required before STL dimensions are
  frozen.

## Hand-off

### Verified facts

- V1 two-part geometry is sealed in `6841cd7`; V2 one-part ball-socket geometry is sealed in
  `3632db0`. The user rejected the bowl-shaped socket because of FDM lip weakness and poor
  metal machinability, so the active V3 uses serial hinges.
- The new RED failed because `src.core.domain.hinge_chain` did not exist. After a conscious
  contract amendment for quarter-turn-invariant tendon holes, 13 focused tests pass and the
  TDD weakening ratchet remains green.
- `HingePhalanxSpec` is an immutable, DDD-pure value object: 5 identical links, 4 revolute
  joints, X-Y-X-Y axes, one printable part type, 4.5 mm printed pin bore, and 8.1 mm MR84 seat.
- Blender 5.1 executed `scripts/model_hinge_chain.py` through the addon socket and saved
  `/tmp/blender-mcp-hinge-chain/hinge_chain_4dof.blend` plus assembly and print-layout PNGs.
- Independent Blender oracle observed 5 printable objects plus 3 layout objects sharing one
  mesh, rotations `0/90/0/90/0`, axes `J1_X/J2_Y/J3_X/J4_Y`, and the declared standard
  hardware contract.
- The public local Streamable HTTP MCP endpoint exposed nine tools and successfully called
  `check_print_readiness`. The report completed without truncation, non-manifold findings,
  or intersections: 3 display objects, 11,616 triangles, about 35,001 mm³ aggregate volume,
  and 14,625 mm² aggregate surface area.
- The new `hinge_chain.py` passes the external DDD domain-purity sentinel in isolation.
- A fresh-context visual round 2 passed every rubric item A-H: five repeated phalanxes,
  distinct male/female hinge geometry, four alternating X/Y joints, visible pins and bearing
  rings, four traceable tendon guides, readable hardware text, and uncropped print views.
- `scripts/ci.sh --real` passes T1 static/build gates, T2 Python/Web tests, and all T3 real
  Blender REST, MCP, readiness-fixture, and batch/Undo oracles.
- A FileProvider incident was root-caused during deployment: dataless API sources and the old
  `web/node_modules`/`web/dist` caused EAGAIN and Tailwind scanning stalls. Tracked sources
  were materialized, dependencies rebuilt from the lockfile, and formal ports 19504/19505/
  9876 returned healthy with Blender connected.

### Open failures

- Print-readiness remains `review`: across three display orientations the approximate ray
  check reports 930 sampled thin-wall faces and the 45-degree profile reports 1,601 overhang
  faces. The designed radial lug wall is 2.45 mm; curved bore/counterbore regions still need
  slicer inspection and a physical coupon.
- Neutral tendon routes align under every 90-degree link rotation, but bent-chain tendon
  rubbing, maximum articulation, backlash, bearing press fit, and fatigue are not physically
  validated.
- Old dataless dependency backups are temporarily isolated under `.git/codex-derived-backups`
  because moving them across the FileProvider boundary blocks; they are not source or part of
  the worktree and should be removed after the provider permits local deletion.
- The earlier Tailnet gateway HTTP 502 has not been reverified in this mechanical slice; local
  identity-protected MCP and the Blender socket are healthy.

### Next step

- Obtain human shape acceptance, then create and print a compact male/clevis/pin/MR84 fit
  coupon before freezing STL tolerances or attempting a motorized tendon test.
