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

- Task index now explicitly retains original room quantitative gaps in Lane A; T1/T2 passed again in `/tmp/full-cast-lane-index-ci.log`. No geometry or runtime change.

- B metadata contract is test-first: six named one-shot effects (8 frames, 128×128, 12fps), six items (ground 128×192 with foot anchor; inventory 64×64). Invalid coverage, frames, timing, paths, scale, anchors and loops reject before publishing. Focused result: 10 intended RED failures, then two boolean-as-number RED failures → 19 total tests passed.
- Reuse review (2026-10-02): [Blender Spritesheet Renderer](https://github.com/chrishayesmu/Blender-Spritesheet-Renderer) and [Phaser animations](https://docs.phaser.io/phaser/concepts/animations), [blend modes](https://docs.phaser.io/phaser/concepts/display/blend-mode). Keep existing generator runner, bpy render and Pillow publisher; use existing Phaser animation boundary. No upstream code copied or new dependency introduced. NORMAL alpha blend is the portable baseline; effect one-shots do not own inventory or quest state.

- B contract full T1/T2 passed (`/tmp/feedback-contract-final-ci.log`); no bpy, geometry or runtime capability changes in this checkpoint. 5S scan still reports baseline hand-document link candidates outside this task; do not treat it as a clean scan.

### Open failures

- No asset or real-Blender gate failures. Full PVR public journey is tracked in its living-world verification report.
- This source checkout retains unrelated historical hand-task snapshots; their progress remains owned by the main Blender checkout.

### Next step

- Finish isolated courier public validation, then connect the B metadata contract to actual Blender models, 48 effect frames and twelve item images, saved-file rerender validation and a playable feedback showcase. B assets/rendering/integration are not yet delivered; C and original-room gaps remain in scope.
