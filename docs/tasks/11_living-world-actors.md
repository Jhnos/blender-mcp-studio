# Living-world actor slice

User authorized continued implementation of PVR's living-world asset plan.
First delivery: traveler and guide, editable shared rig, four directions and idle/walk/interact,
two portraits, nine conversation/quest/delivery markers; independent encounter pack with guide,
parcel retrieval and return. Remaining four-role A/B/C expansion stays in PVR STATUS.

## Hand-off

- Source contract: PVR docs/12_gameplay_campaign/development/P6-living-world-assets.md.
- Asset malformed-contract tests start RED before generator implementation.
- Use existing headless Blender generator workflow; no public runtime capability changes.
- Saved-file verifier must reopen rig/actions, project feet and rerender sample frames.
- Full CI and real tier required; source branch remains independent of unrelated hand work.
- Saved files and 96frames/9markers generated; named actions, rooted rigs, full-face portrait bounds and regenerated sample pixels verified.
- Next: retain source and verify formal PVR gameplay plus independent visual targets before publication claims.
