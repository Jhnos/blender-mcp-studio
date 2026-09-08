# Universal world-kit expansion

User request: broaden the facets covered by reusable Veilroom assets.

## Contract

18 new editable low-poly modules across architecture, outdoors and props; same metre grid,
64px/m projection and (0.5,0.75) object anchor. Both existing palettes are retained.
Gate, lever, pressure plate and crystal have distinct alternate states. Published atlases
use the existing 15-frame format per family, with floor at frame 0; no public DTO changes.
Deliver a browsable catalog and three assembly examples per palette plus Tiled layouts.
Visual states are assets; they do not by themselves implement new gameplay rules.

## Trace / verification plan

| Requirement | Artifact oracle | Failure fixture |
|---|---|---|
| 18 module kinds × two palettes | decoded manifest, reopen blend meshes/materials | missing family/variant |
| same grid and footpoint | dimensions, collection origin, rendered origin metadata | wrong anchor / cropped alpha |
| four state pairs change output | pixel and geometry differential at fixed camera | duplicate state PNG |
| two palettes reuse geometry | equal dimensions/placement, different pixels | palette flag dropped |
| game-ready family atlases | frame layout/count, PNG decode, Tiled reader | invalid frame / missing image |
| real presentation | six assembled scenes; independent screenshots review | object hidden/cropped/overlapped |
| release stable | public URL/hash checks and source archive | vanished working directory |

## Hand-off

### Verified facts

- Existing room baseline is preserved; expansion is additive.
- 44 sprites, 7 reopened Blender files, six compatible atlases/layouts; geometry, material,
  source visibility, footpoint projection and lever endpoint checks passed.
- Full CI including real Blender saved-file oracle and REST/MCP tiers passed.
- Public read-only gallery has numeric 300/375/1280px sweeps and bounded seeded random evidence;
  screenshot identity and actual download results are retained by Veilroom.

### Open failures

- Original room Lane A gaps remain active in task 09; this expansion does not close them.

### Next step

Preserve the published expansion and its evidence; continue task 09’s existing Lane A work before claiming the whole room campaign complete.
