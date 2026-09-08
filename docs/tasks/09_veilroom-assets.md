# Veilroom universal-room assets

## Goal

Deliver 12 reusable Blender modules, two materials, and one playable 2D spatial map in
Project_Veilroom. User-approved scope: orthographic low-poly sprites, keyboard/touch,
room → corridor → exit, three interactions, persistent inventory and visual state.

## Hand-off

### Verified facts

- Reopened both delivered Blender files; 30 sprite variants and 1156 assembled meshes passed inspection; collection instance offsets preserve module origins.
- New Veilroom API journey covers invalid movement, visiting exit before obtaining key,
  board, chest, once-only inventory, exit completion and fresh SQLite service reload.
- Blender REST/MCP/readiness/batch real-machine gates passed.
- Source and rebuild commands: [package README](../../models/universal-room/README.md).

- The asset branch passed full local CI and every real Blender tier on the integrated framework-document base.

### Open failures

- Complete Lane A is not established. Gameplay journeys do not prove all controls, numeric viewport
  checks, module seams, material outcome differentials, cleanup or reversible formal delivery.
- Aesthetic acceptance is not assigned to the user: quantifiable experience stays in Lane A.
- Concurrent main updates twice removed the asset merge. The pushed branch preserves source;
  stable integration and delivery-path checks remain the agent's responsibility.
- Canonical Lane definition and per-requirement evidence audit live in Project_Veilroom under
  docs/12_gameplay_campaign/verification/universal-room/00-INDEX.md and ../01-scope.md.

### Next step

Follow the canonical Lane A plan: fixture lifecycle, UI sweep/random/oracles, artifact comparisons,
independent visual checks and stable formal integration. Do not ask the user to replace these checks.
