# Universal Room — Blender → Veilroom

Editable, metre-scale low-poly modules for a top-down 2D game. Original geometry and
procedural materials authored for this project; no external texture downloads are required.

## Open and reuse

- `universal-room.blend`: two material variants, organised into named collections.
- `warehouse.blend`: the assembled room, corridor and exit. `UR_warehouse` owns the map objects.
- `wood-stone-preview.png`, `metal-preview.png`: catalogue views.
- `warehouse-preview.png`: assembled scene preview.
- `manifest.json`: dimensions, collection names, frame order, image size and anchor.
- `verification.json`: independent reopening of both Blender files and inspection of meshes/materials/images.

The twelve modules are floor, wall, corner, doorframe, door leaf, table, chair,
chest, cabinet, shelf, lamp and noticeboard. Door/chest have open and closed states;
`wall_side` is the wall rotated 90°. Each material variant has 15 rendered frames.

Each floor occupies 1 × 1 m and renders at 64 × 64 px. Object sprites are 128 × 192 px,
64 px per horizontal metre, with their ground origin at (64,144): normalised anchor
(0.5,0.75). The object camera looks from (0,-8,12) with orthographic scale 3 m.
Collection instance offsets preserve the same ground origin even though the catalogue spreads
modules apart. Append a collection and instantiate it to place a module at a grid origin.

## Regenerate and publish

Run from this repository:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python scripts/model_universal_room.py
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python scripts/verify_universal_room.py
uv run --no-project --with pillow python scripts/package_universal_room.py /Users/bearmacmini/Project_Veilroom/src/veilroom/interface/web/static/game-content/universal-room
```

The generator reuses `blender_generator_runner` and the material primitives. It runs
in an isolated Blender process and does not replace the live addon scene. `layout.tmj`
is the frozen source snapshot from Veilroom's `universal-room/maps/warehouse.tmj`.
Change the Veilroom map first, then copy its updated snapshot here before regenerating.
The publisher rejects empty, cropped and incorrectly sized sprites, and creates 4-column
PNG atlases, separate floor textures and a checksum manifest. Checksums identify the
published bytes, not a claim of byte-identical rendering across Blender versions.

In Veilroom: open **故事與世界**, create a world using **轉角倉庫 · 3D 素材試玩**,
then create a storyline and choose **圖形遊玩**. Walk below the noticeboard and chest,
then follow the corridor to the tile below the exit door. The touch arrows and keyboard
use the same move endpoint; inventory and object states survive reload.
