# Changelog

本專案所有值得注意的變更記錄於此。格式依 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)；
版號依全域 version-management 規範（base36 固定寬度 VXX.XX.XXX；任何修改至少 bump 段3）。

## [Unreleased]

### V01.02.000

#### Fixed

- The octopus hand's base joint swung the wrong way. The palm socket faced along its arm's
  radius, so the pin lay along the radius too and the first joint swung the arm sideways
  around the palm — it opened and closed nothing. `palm_socket_twist_deg` now turns each
  socket a quarter turn so the pin lies across the radius and the arm carries in toward the
  palm centre and back out, which is the joint that actually closes a grip. Every body above
  is twisted to match, so the ears still meet, and the pins follow the same alternation.
  Measured in the live scene: the base pin axis sits 90.0° to the radius at all five stations.

#### Changed

- `octopus_hand_tips.json` no longer sweeps the tip against a copy of itself. That measured a
  joint the hand does not have — nothing mates above a tip — and it passed for an unrelated
  reason before the axes changed and failed for an equally unrelated one after. What replaces
  it is a spec invariant: every tip feature starts above the body's mid-plane, clear of the
  ears the tip actually hangs from. `tip_feature_fuse_mm` moved into the spec so that
  clearance is a checked dimension rather than a constant in the generator.
- `docs/LESSONS_LEARNED.md` records the class: a proxy test whose configuration does not exist
  in the product carries no information green or red, and looks identical to a real guard.

### V01.01.001

#### Changed

- `docs/tasks/04_octopus-hand-v1.md` records that the octopus hand's visual rubric has not
  been judged by a fresh context yet. The rubric existing is not the rubric having passed,
  and the hand-off was letting the next reader assume otherwise.

### V01.01.000

#### Added

- Octopus hand V1: a five-armed print-in-place gripper built entirely from new files. A
  pentagonal palm carries five V6 biaxial arms, twenty tendon holes and one central wire
  channel; each tip gets four cross-drilled cable eyelets and an inward claw. `OctopusHandSpec`
  composes `BiaxialHingeSpec` rather than subclassing it, so V6's contract is untouched — no
  V6 domain, generator or `models/` file changed.
- The printer bed is a spec invariant, not a comment: `upright_footprint_mm > max_bed_mm`
  raises. Splayed flat the hand needs 275.9 mm and does not fit a 220 mm bed; upright it
  needs 133.3 mm square by that bound and exports at 126.8 × 120.6 × 113.8 mm.
- Two artifact contracts, `octopus_hand.json` and `octopus_hand_tips.json`, green on real
  Blender with no skips. Between them they measure per-arm collision, **inter-arm** collision
  (twenty bodies sorted level by level), tip-to-tip clearance, a −34°…+34° joint sweep for
  both the plain body and the tip, an open wire channel, an open cable path through the tip,
  and an untruncated readiness report.
- `docs/verification/octopus-hand-v1.md` — target, evidence table, a ten-item visual rubric
  and the evidence boundaries.

#### Changed

- `docs/LESSONS_LEARNED.md` records the class this build walked into: a feature that does not
  change an object's bounding box is invisible to dimension readback. A hidden object drops
  out of Blender's depsgraph and its Booleans are silently skipped, so the tip exported
  byte-identical to the plain body while fourteen contract checks stayed green. The generator
  now fails loud if the tip's face count did not grow.

### V01.00.00C

#### Fixed

- `BlenderSocketClient.is_connected` now folds in the reader's EOF instead of trusting
  `StreamWriter.is_closing()` alone. `is_closing()` reports whether *this* side asked to
  close, so it stayed True after Blender exited and `/api/health` kept answering
  `blender: connected` with port 9876 shut — the field `docs/30-verification.md` tells
  reviewers to trust as the readiness signal.
- A dropped addon connection now raises `BlenderConnectionError` instead of degrading into
  a decode failure. `send_command` broke out of its read loop on the peer's EOF and handed
  the stump to `_decode_response`, so a dead engine surfaced as `JSONDecodeError` and sent
  the reader hunting for a data-format bug. `LESSONS_LEARNED.md` recorded this class and
  its prevention item in V01.00.00B; this implements it.

#### Added

- `tests/unit/adapters/test_blender_socket_liveness.py`: three tests over a real loopback
  server (no mock socket) pinning both halves of the signal — false once the peer hangs up,
  true while the peer holds the socket.

#### Changed

- `docs/LESSONS_LEARNED.md` records the class behind the above: a connection flag that only
  reads local state cannot be a readiness signal, and the V01.00.00B lesson's premise
  ("health honestly said disconnected") held only for one startup ordering.

### V01.00.00B

#### Fixed

- `deploy/launchd/install.sh blender` now waits for the addon listener and restarts the API
  as well. Restarting Blender orphans the socket the API holds — it connects once at startup
  and never reconnects — so a bare `blender` install left the API answering from a dead
  socket. `/api/health` correctly said `disconnected`, but the data path failed as
  "scene info is missing fields" (422) rather than "Blender is unreachable" (503), which
  points a reader at the payload instead of the connection.

#### Added

- `scripts/check_installed_plists.py` and its eight tests: a real-tier gate asserting every
  installed LaunchAgent resolves to this checkout. `docs/12-deployment.md` rule 7 called a
  clean diff between installed plist and template "the contract" and then left it to manual
  checking; this is the missing machine check.

#### Changed

- `docs/LESSONS_LEARNED.md` records two more classes found while finishing this release:
  restarting a depended-on service does not restore the side that depends on it, and a
  filesystem sync service disguises itself as bugs in git, npm and the agent.

#### Verified

- `scripts/ci.sh --real` — all hard gates green, including the new installed-LaunchAgent
  gate and all four real-machine tiers against live Blender.

### V01.00.00A

#### Fixed

- The four T3 verifiers gained a `src.` import in V01.00.009 and could not run: `ci.sh`
  executes them as subprocesses, where nothing puts the repository root on `sys.path`.
  T1 and T2 stayed green because pytest does. Each now carries the `PROJECT_ROOT` block
  that `generated_artifact_verify_real.py` already had.
- Removed two `from src.…` lines that an automated edit had inserted *inside* the
  triple-quoted Blender scripts these files build. Blender executes those strings in its
  own interpreter, where this repository does not exist.

#### Added

- `tests/unit/scripts/test_embedded_blender_code.py` — no project import may sit inside a
  Blender code string. Nothing else can catch this: ruff, mypy and the narrowing gate all
  see a string, and no test tier executes it. Blender's own dialect is allowed.

#### Changed

- The eslint wiring proof runs the installed binary instead of `npx`, and asserts that
  binary exists. `npx` performs its own resolution and stalled under load, which made the
  gate flake; runtime drops from 7.7s to 2.0s.
- `docs/LESSONS_LEARNED.md` records the environment root cause found while verifying this
  release: the project directory is inside macOS Desktop-and-Documents iCloud sync, which
  produced the " 2" conflict copies, the broken git ref, the dataless `web/dist` files and a
  corrupted `web/node_modules` — four symptoms that each looked like a different tool's bug.

#### Verified

- `scripts/ci.sh --real` — all hard gates green, including all four real-machine tiers
  against live Blender through the Tailnet endpoint with the addon socket as an
  independent oracle.

### V01.00.009

#### Fixed

- Repaired `POST /api/refine`, which called `adapter_factory.create_llm_adapter()` — a method
  that exists on neither the port nor the concrete factory. `app.state` returns `Any`, so mypy
  could not see the call, and the only factory double in the suite was a bare `MagicMock` that
  answers to any attribute name. The endpoint had no test at all; it has two now.

#### Changed

- Domain errors map to HTTP status in one place (`api/main.py`). Fourteen hand-written
  clauses across four routers are gone; the same condition no longer produces `str(exc)` in
  some endpoints and `f"Blender unreachable: {e}"` in others.
- Use cases are assembled at the composition root instead of per request in routers, which is
  what makes their wiring type-checked.
- `api/routers/scene.py` (749 lines, seven services) is split into eight routers by the service
  each owns; the largest is now 171 lines. The OpenAPI route set is unchanged.
- Every `bpy` statement the REST layer needed moved to `src/adapters/blender_scripts/`, where
  each operation has a name and returns a typed `ScriptOutcome`. Transport failures now
  propagate to the shared handler instead of being swallowed into a 500 by some routes and
  turned into a 503 by others.
- Five copies of JSON narrowing collapse onto `src/infrastructure/narrowing.py`, which grows a
  predicate layer plus a `required()` combinator that keeps each caller's exception type and
  message — those strings reach REST clients verbatim as a 422 `detail`.
- Five frontend call sites share `runTracked`; the print-readiness inspection now reports into
  the operation store like every other operation instead of only its own panel state.
- `scripts/` joins every Python gate (ruff, format, mypy strict, container-narrowing). It was
  outside all of them, including the gate's own source file.
- The container-narrowing gate now recognises `Mapping`, `Sequence` and the other abstract
  container types. It had listed only `dict` and `list` while four shipped call sites used the
  abstract names.

#### Added

- Gates with should-fire and should-pass fixtures for each new rule: no hand-mapped domain
  errors, no use-case construction or `bpy` source in routers, no re-defined script primitives,
  a 400-line file budget warning at 380, DCC doc rules, and an eslint rule proven by driving
  real eslint over stdin.
- `tests/unit/scripts/test_check_container_narrowing.py` — the blocking gate had no test of
  its own, which is how its blind spot survived.
- `docs/DEFERRALS.md` recording three deliberate non-abstractions with firing triggers.
- `scripts/blender_generator_runner.py` replacing the clear/hide/build/restore wrapper that
  three generators each carried.

#### Removed

- Archived to `scripts/archive/`: two generators and their render adapters with zero
  references anywhere, two cat-stand demos, and an unreferenced use case. Nothing deleted.

### V01.00.008

#### Changed

- Restructured `docs/` into a DCC tree: a `README.md` navigation table with a
  "when to read" column, numbered topic files (`00-context`, `01-architecture`,
  `10-runtime-ssot`, `11-mcp-clients`, `12-deployment`, `20-conventions`,
  `30-verification`), and `[[wikilink]]` cross-links. Renames use `git mv`, so
  history follows each file.
- Collapsed seven duplicated fact groups into single sources. Ports, routes,
  canonical URLs and environment variables now exist only in
  `docs/10-runtime-ssot.md`; CI tiers, commands and "what does not count as
  evidence" only in `docs/30-verification.md`. Other documents link instead of
  restating.
- Rewrote `docs/KNOWLEDGE.md` as a knowledge-placement map only; navigation moved
  to `docs/README.md`, removing the second, drifting navigation surface.
- Corrected stale statements verified against the running system: the task index
  and task 02 said PR #4 was open (merged as `901cb53`); engineering standards
  said two LaunchAgents run (three plists exist) and called the service an
  "MCP-style HTTP API"; `deploy/launchd/README.md` omitted the `blender` install
  target that `install.sh` supports.

#### Added

- Added `tests/unit/core/test_docs_dcc.py`, a hard gate for three DCC rules:
  wikilinks resolve, every live doc is reachable from the navigation root within
  two hops, and ports appear only in their SSOT file. Each rule ships with
  should-fire and should-pass fixtures, so a guard that degenerates into
  "always fails" or "never fires" is itself caught.

#### Removed

- Removed `web/README.md` (unreferenced Vite template boilerplate) and five
  cloud-sync duplicate files under `web/dist/`.
- Archived `docs/TECH_SPEC.md` to `docs/archive/2026-09-tech-spec-superseded.md`
  and removed `docs/ENGINEERING_STANDARDS.md` after distributing their content
  (§1 scope to `00-context`, §11 plist rules to `12-deployment`, the remainder to
  `20-conventions`, `10-runtime-ssot` and `30-verification`).

### V01.00.007

#### Added

- Added the checksum-controlled V6 print package under `models/biaxial-hinge-v6/`: five
  millimetre STL coupons and parts, the complete `.blend` source, and a `manifest.json`
  with independent byte-length, SHA-256, triangle-count and dimension readback.
- Added `scripts/publish_print_package.py`, an allowlisted promoter from ignored
  `tmp/biaxial-hinge-v6/` output into the tracked package, with a package readback test and
  a CLI bootstrap regression test.
- Added `.gitattributes` marking `.stl` and `.blend` files as binary.

#### Changed

- Documented the promoted package in the README, V6 hand-off, verification guides and
  project Skill; `tmp/` stays ignored working state and is never unignored wholesale.

### V01.00.006

#### Added

- Added the V6 Ø36 mm repeatable hinge body with biaxial in-disc roots, a clear Ø10 mm
  sensor channel, four tendon bores and a reduced 19 mm pitch.
- Added two 3D-print PIN workflows using the same body: a two-body print-in-place coupon
  with double-headed captive pins, and a six-part coupon with grooved pins plus C clips.
- Added reusable retention geometry, PIP/separate presentation adapters, declarative
  readiness contracts, world-space hardware probes and displaced stop-contact evidence.

#### Changed

- Generalized the V5 body and pin builders to accept an injected immutable specification,
  preserving the earlier model while avoiding a second copy of its Blender construction.
- Archived the superseded V5 task contract and updated the project Skill, artifact workflow,
  V6 hand-off and independent A–I visual evidence.

#### Fixed

- Synchronized Blender view-layer transforms before hidden-layout export/BVH measurement,
  preventing stale world matrices from collapsing split hardware to the origin.
- Separated product and presentation object prefixes so diagnostic render copies cannot
  contaminate readiness selection, intersection counts or truncation state.

### V01.00.005

#### Added

- Added the V5 in-disc hinge prototype: Ø34 mm body, shallow reinforced roots, a clear
  Ø10 mm sensor channel, four tendon bores and separately printable Ø4 mm headed pins.
- Added body/pin/coupon millimetre STL outputs, detail/top views, JSON-driven hole/slope/
  hardware probes, fail-closed evidence tests and independent visual acceptance targets.

#### Changed

- Extracted shared Blender mesh primitives for V4/V5 reuse; preserved public REST/MCP DTOs.
- Superseded V4 task notes with a V5 hand-off, preserving V4 history and generated files.
- Documented sequential real-verification transactions, Blender STL import scale 0.001,
  and prototype limits: body support warnings, untested physical fit and missing pin retention.

### V01.00.004

#### Added

- Added nine short repeated hollow modules, eight alternating side-mounted hinges, a clear
  10 mm sensor-wire channel, four tendon routes and a single-module millimetre STL export.
- Added reusable geometry, render and explicit-mesh export helpers plus a JSON-driven
  generator/oracle/MCP verifier with independent binary STL readback and sampled joint motion.
- Added RED-to-GREEN tests for geometry constraints, artifact parsing, fail-closed reports,
  missing motion samples and assembly-camera restoration; documented the reusable workflow.

#### Fixed

- Removed static and bent bridge/lug collisions by deriving bridge placement from the
  motion envelope; real geometry checks pass 15 discrete poses from −34 to +34 degrees.
- Prevented overlapping/cropped print layouts and camera state leaking from the last render
  into the saved assembly file. Thin-wall and support warnings remain visible for trial prints.

### V01.00.003

#### Added

- Added an immutable hinge-phalanx domain contract, RED-to-GREEN validation tests, and a
  Blender generator for five identical links sharing one mesh across four serviceable
  X-Y-X-Y revolute joints.
- Added deterministic assembly and three-view print-layout evidence with 4 mm pins, optional
  MR84 4x8x3 bearing interfaces, and four continuous tendon guides.

#### Changed

- Replaced the active bowl-shaped ball-socket concept with alternating single-axis clevis
  hinges that are suitable for FDM prototyping and map directly to machined pins and bearings.
- Changed tendon routing to a quarter-turn-invariant cross pattern so the same printed part
  can be installed at alternating 0/90-degree orientations without changing hole alignment.

### V01.00.002

#### Added

- Added an immutable one-part vertebra contract and Blender generator: three instances share
  one mesh, while two ball-socket interfaces provide four named X/Y rotational axes and four
  continuous tendon routes.

#### Changed

- Replaced the earlier disc-and-cross-gimbal prototype with one repeatable 42 mm vertebra
  carrying a 10.0 mm male ball and 10.6 mm Y-split female socket.
- Removed the whole-part bevel after real MCP analysis exposed slot-edge defects; the final
  report has no non-manifold or intersection findings and retains honest support warnings.

### V01.00.001

#### Added

- Added an immutable, validated two-cell tendon-joint specification with RED-to-GREEN tests
  and a Blender 5.1 generator for three female-yoke discs, two male cross-gimbals, four
  named hinge axes, four continuous tendon routes, and separated print-layout evidence.

#### Changed

- Made concept renders deterministic in a shared Blender runtime by isolating unrelated
  scene objects, using scale-stable Workbench colors, and restoring prior visibility.
- Reduced generated mesh density and removed degenerate gimbal geometry so MCP print
  readiness completes without truncation; remaining support and tip-snap warnings stay
  visible as design-review items.
- Archived the accepted project-knowledge 5S task and opened the tendon-joint task as the
  sole current progress record.

### V01.00.000

#### Added

- Added project task/checkpoint SSOT, knowledge 5S budgets, and a repository-specific
  `blender-mcp-studio` Skill.
- Established the base36 `VERSION` release SSOT and exposed it through FastAPI metadata.
- Added a machine gate for broken local Markdown links, including archived documentation.

#### Changed

- Consolidated agent instructions in `AGENTS.md`, with `CLAUDE.md` importing the shared rules.
- Archived the completed 2026-07 campaign and replaced the legacy knowledge monolith with a
  current navigation map.
- Made production startup delegate to launchd and reserved Vite port 5173 for foreground dev.

#### Deprecated

#### Removed

- Removed stale local agent permission entries and generated cache/build artifacts from the
  working directory; secrets, dependencies, runtime databases, and launch configuration remain.

#### Fixed

- Made `install.sh all` wait for measured Blender addon readiness before starting the API,
  preventing a one-shot startup connection from remaining disconnected after a cold boot.

#### Security
