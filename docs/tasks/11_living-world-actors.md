# Living-world actor slice

**Status:** ACTIVE

User authorized continued implementation of PVR's living-world asset plan.
Full A delivery: four original roles, shared editable rig, four directions and idle/walk/interact,
four portraits and eighteen event markers. Keep the released two-role encounter independently playable;
full courier gameplay and subsequent B/C expansion stay in PVR STATUS.

## Hand-off

### Verified facts

- Source contract: PVR docs/12_gameplay_campaign/development/P6-living-world-assets.md.
- Asset malformed-contract tests start RED before generator implementation.
- Use existing headless Blender generator workflow; no public runtime capability changes.
- Saved-file verifier must reopen rig/actions, project feet and rerender sample frames.
- Full CI and real tier required; source branch remains independent of unrelated hand work.
- Saved files and 192frames/18markers generated; named actions, rooted rigs, full-face portrait bounds and regenerated sample pixels verified.
- `scripts/ci.sh --real` passed, including saved Blender file reopening and actual REST/MCP checks.
- Independent full-cast asset review confirms four full-face portraits, unclipped 192 sprites, full-body preview and eighteen distinguishable markers.

- Full-cast final CI: `/tmp/living-full-cast-ci-final.log`; independent review: `tmp/living-full-cast-release/visual-review.md`.
- Preview expansion originally clipped outer characters; corrected orthographic framing and added alpha-bound publishing rejection.

- Source editing instructions now specify render isolation and exact assembled-preview camera settings; doc-only T1/T2 passed (`/tmp/full-cast-source-doc-ci.log`). Blend geometry is unchanged from the real-verified source.

### Open failures

- No asset or real-Blender gate failures. Full PVR public journey is tracked in its living-world verification report.
- This source checkout retains unrelated historical hand-task snapshots; their progress remains owned by the main Blender checkout.

### Next step

- Complete courier public game evidence in PVR; then implement six effects and six items under the existing plan, keeping the complete A/B/C scope active.
