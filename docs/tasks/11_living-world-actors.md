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

- Six editable item models and twelve RGBA images now exist in `models/living-items/`; source scene shows the six-item preview on open. Saved-file verification rerenders all twelve and requires exact pixel equality, material/feature geometry, foot anchor and transparent margins. Independent visual review inspected all twelve plus preview; PASS, evidence `tmp/living-items-evidence/`.
- Six editable effects now supply 48 RGBA frames, 8 distinct poses per effect, 12fps one-shot metadata and a source preview in `models/living-effects/`. Saved-file verification rerendered all 48 with exact pixel equality and checked animated bounds/alpha margins. Independent review inspected 48 frames plus preview; all six written targets passed.
- Full `scripts/ci.sh --real` passed after the recovery and ownership fixes: T1/T2, effect/item/actor/world-kit saved-file checks, loaded services, REST, MCP, readiness and batch operations. Durable log copy: `tmp/living-feedback-evidence/living-feedback-full-ci.log`. This seals source assets and verification, not playable B integration.
- 5S scan still lists baseline hand-document link candidates owned by the main checkout; no new task-specific finding was used to claim a clean whole-repository scan.

- Feedback publisher now binds evidence to source blend/image SHA256, rejects stale/incomplete/duplicate/failing records (seven RED→GREEN tests), and creates six effect plus two item atlases, twelve HTML-friendly item images, two previews and a bounded source ZIP. All 60 atlas cells were compared to their original bytes; 22 PNGs total 822,370 bytes, below the 4MiB budget. Pinned publishing runtime: Pillow 12.3.0.
- Complete `scripts/ci.sh --real` passed for the publisher, including refreshed saved-source hashes and the actual publisher gate (`/tmp/feedback-publisher-real-ci.log`). Release staging: `tmp/living-feedback-release/feedback.json` and `living-feedback-source.zip`.
- PVR integration checkout created at `/Users/bearmacmini/Project_Veilroom_Feedback`, branch `codex/living-feedback`, starting from `ea760a1`; its main checkout has independent verification edits, so do not overwrite/stage those. Merge and remove this integration worktree after the playable B release is verified.

### Open failures

- No remaining failure in this source checkpoint's complete gate. The initial run's five service failures and concurrency are retained in `tmp/living-items-evidence/`; restarting API/Web restored logs and scene responses, without restarting Blender or changing the user scene. No owned fixtures remained on read-only inspection.
- REST verifier broad cleanup and false-success exit behavior were repaired: unique nonce, exact owned names, finally cleanup, cleanup failure propagation, negative observations fail the process. Five discriminating tests went RED→GREEN and the live REST gate passed.
- Full PVR public validation and release are being modified by another active work stream in that checkout; inspect its current STATUS/evidence before writing there.
- This source checkout retains unrelated historical hand-task snapshots; their progress remains owned by the main Blender checkout.

### Next step

- Integrate the published feedback package in the PVR feedback worktree: optional map catalog, semantic consequence projection, once-only sprite playback, inventory pictures and actual playable uses. Reuse resolved_consequence plus instance_id/choice_id/replayed from the existing choice response. Keep old content/save identities intact. B runtime/reduced-motion/deduplication, C and original-room gaps remain required.
