# Living-world actor slice

**Status:** ACTIVE

User authorized continued implementation of PVR's living-world asset plan.
First delivery: traveler and guide, editable shared rig, four directions and idle/walk/interact,
two portraits, nine conversation/quest/delivery markers; independent encounter pack with guide,
parcel retrieval and return. Remaining four-role A/B/C expansion stays in PVR STATUS.

## Hand-off

### Verified facts

- Source contract: PVR docs/12_gameplay_campaign/development/P6-living-world-assets.md.
- Asset malformed-contract tests start RED before generator implementation.
- Use existing headless Blender generator workflow; no public runtime capability changes.
- Saved-file verifier must reopen rig/actions, project feet and rerender sample frames.
- Full CI and real tier required; source branch remains independent of unrelated hand work.
- Saved files and 96frames/9markers generated; named actions, rooted rigs, full-face portrait bounds and regenerated sample pixels verified.
- `scripts/ci.sh --real` passed, including saved Blender file reopening and actual REST/MCP checks.
- Independent asset review round 2 confirms full-face portraits, unclipped sprites and distinguishable markers.

### Open failures

- No asset or real-Blender gate failures. Full PVR public journey is tracked in its living-world verification report.
- This source checkout retains unrelated historical hand-task snapshots; their progress remains owned by the main Blender checkout.

### Next step

- Expand the remaining guard/artisan roles from the PVR living-world requirement matrix after sealing the two-role gameplay evidence; preserve the shared camera, root and clip contracts.
